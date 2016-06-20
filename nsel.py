#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

from bs4 import BeautifulSoup
from time import strptime, mktime, strftime
from os.path import exists
from hashlib import sha256
from lxml.html.clean import Cleaner

import flask
import requests

from cookies import ShelvedCookieJar

LOGIN_URL = 'http://nsel.cz/'
MAIN_URL = 'http://nsel.cz/cs/NewsSel/QueryRes/1'
BODY_URL = 'http://nsel.cz/cs/NewsSel/GetDetailPartial?showRestriction=140&id=%s'

cleaner = Cleaner()

cache = {}

def fix_time(s):
    t = strptime(s, '%d.%m.%Y %H:%M:%S')
    return strftime('%Y-%m-%d %H:%M:%S +1000', t)

def now():
    return strftime('%Y-%m-%d %H:%M:%S +1000')

def fetch_body(s, post):
    if post not in cache:
        r = s.get(BODY_URL % post)
        bs = BeautifulSoup(r.text, 'html5lib')
        body = str(bs.select_one('div.text'))
        cache[post] = cleaner.clean_html(body)

    return cache[post]

def iter_posts(s):
    r = s.get(MAIN_URL)
    bs = BeautifulSoup(r.text, 'html5lib')

    for tr in bs.select('#listTable tr')[:-1]:
        title = tr.select_one('.text') or tr.select_one('.textRed')

        if 'Kurzy devizového trhu' in title.text:
            continue

        yield {
            'id': tr.attrs['id'],
            'title': title.text,
            'time': fix_time(tr.select_one('span').text),
            'body': fetch_body(s, tr.attrs['id']),
        }


def make_app(login, password):
    app = flask.Flask(__name__)
    s = requests.Session()
    s.cookies = ShelvedCookieJar('cookies')

    secret = (login + ':' + password).encode('utf8')
    valid_token = sha256(secret).hexdigest()[:16]
    print('Feed at /{}/main.rss'.format(valid_token))

    s.post(LOGIN_URL, [
        ('UserName', login),
        ('Password', password),
        ('RememberMe', 'true'),
        ('RememberMe', 'false'),
    ])

    @app.route('/<token>/main.rss')
    def main_rss(token):
        if token != valid_token:
            return 'Denied', 401

        pub_date = now()
        posts = list(iter_posts(s))

        return flask.render_template('main.xml', **locals()), 200, {
            'Content-Type': 'application/rss+xml; charset=UTF-8',
        }

    return app


if __name__ == '__main__':
    import sys
    app = make_app(*sys.argv[1:])
    app.run(host='::', port=8888)


# vim:set sw=4 ts=4 et:
