#!/usr/bin/python3 -tt
# -*- coding: utf-8 -*-

from sys import stderr
from bs4 import BeautifulSoup
from datetime import datetime
from os.path import exists
from hashlib import sha256
from lxml.html.clean import Cleaner

import flask
import requests

from cookies import ShelvedCookieJar

LOGIN_URL = 'http://nsel.cz/'
LOGOUT_URL = 'http://nsel.cz/cs/NewsSel/LogOff'
MAIN_URL = 'http://nsel.cz/cs/NewsSel/QueryRes/1'
BODY_URL = 'http://nsel.cz/cs/NewsSel/GetDetailPartial?showRestriction=10000&id=%s'

cleaner = Cleaner()

cache = {}

def fix_time(s):
    t = datetime.strptime(s, '%d.%m.%Y %H:%M:%S')
    return t.strftime('%a, %e %b %Y %H:%M:%S +0000')

def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S +1000')

def fetch_body(s, post):
    if post not in cache:
        r = s.get(BODY_URL % post)
        bs = BeautifulSoup(r.text, 'html5lib')
        body = str(bs.select_one('div.text'))
        print(' * Fetched post', post, file=stderr)
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

def remove_obsolete(posts):
    titles = {}

    for post in posts:
        titles[post['title']] = post

    for post in sorted(titles.values(), key=lambda post: post['id']):
        yield post

def get_logout_token(s):
    r = s.get(MAIN_URL)
    bs = BeautifulSoup(r.text, 'html5lib')

    elem = None

    for form in bs.select('form'):
        if form.attrs.get('name') == 'logoutForm':
            elem = form.select_one('input')
            break

    if elem is None:
        return ''

    return elem.attrs['value']

def do_login(s, login, password):
    print(' * Logging in...', file=stderr)
    r = s.post(LOGIN_URL, [
        ('UserName', login),
        ('Password', password),
        ('RememberMe', 'true'),
        ('RememberMe', 'false'),
    ])

    cache.clear()
    right_content = '/cs/NewsSel/QueryRes/' in r.text

    if r.ok and right_content:
        print(' * Successfully logged in!', file=stderr)
    else:
        print(' * Failed to log in!', file=stderr)

    return r.ok and right_content


def do_logout(s):
    print(' * Logging out...', file=stderr)
    r = s.post(LOGOUT_URL, [
        ('__RequestVerificationToken', get_logout_token(s))
    ])

    if r.history:
        r = r.history[0]
    cache.clear()

    if r.ok:
        print(' * Successfully logged out!', file=stderr)
    else:
        print(' * Failed to log out!', file=stderr)

    return r.ok


def make_app(login, password):
    app = flask.Flask(__name__)
    app.config.update({
        'PROPAGATE_EXCEPTIONS': True
    })

    s = requests.Session()
    s.cookies = ShelvedCookieJar('cookies')

    secret = (login + ':' + password).encode('utf8')
    valid_token = sha256(secret).hexdigest()[:16]
    print(' * Feed at /{}/main.rss'.format(valid_token), file=stderr)

    do_login(s, login, password)

    @app.route('/<token>/login')
    def login_route(token):
        if token != valid_token:
            return 'Denied', 401

        r = do_login(s, login, password)
        return flask.jsonify(result=r)

    @app.route('/<token>/logout')
    def logout_route(token):
        if token != valid_token:
            return 'Denied', 401

        r = do_logout(s)
        return flask.jsonify(result = r)

    @app.route('/<token>/main.rss')
    def main_rss(token):
        if token != valid_token:
            return 'Denied', 401

        pub_date = now()
        posts = list(remove_obsolete(iter_posts(s)))

        return flask.render_template('main.xml', **locals()), 200, {
            'Content-Type': 'application/rss+xml; charset=UTF-8',
        }

    return app


if __name__ == '__main__':
    import sys
    app = make_app(*sys.argv[1:])
    app.run(host='::', port=8888)


# vim:set sw=4 ts=4 et:
