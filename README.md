# ČTK NewsSelect scraper to RSS

Allows to receive ČTK main news using a mobile feed reader with tracking
of seen items. Infrequent restarts to prevent the session from expiring is
advisable. However be careful, the number of active sessions is limited.

# Running

To run the application, just issue:

    python3 nsel.py login password

Please note that the URL under that the feed can be found contains portion
of the login+password hash. To get the token:

    echo -n 'login:password' | sha256sum | cut -c-16

The feed can than be found on:

    http://127.0.0.1:8888/<token>/main.rss

Enjoy!

<!-- vim:set spelllang=en: -->
