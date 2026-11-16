"""Vercel entrypoint.

Vercel's Python runtime looks for a Flask instance named `app` in one of the
supported entry files (app.py, index.py, server.py, main.py, wsgi.py, asgi.py)
or inside src/ or app/. `run.py` is not on that list, so this file re-exports
the same application the local server uses:

    vercel dev      -> http://localhost:3000
    vercel --prod   -> https://<project>.vercel.app

Everything else (database path, writable location, cookie flags, demo data)
is decided in config.py based on the VERCEL environment variable.
"""

from app import create_app

app = create_app()
