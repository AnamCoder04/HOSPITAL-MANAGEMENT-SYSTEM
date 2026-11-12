"""Entry point for the MediCare HMS Flask application.

Run locally with either command:

    python run.py
    flask --app run.py run --debug

The application uses the factory pattern, so this file only builds an app
instance from app.create_app() and (when executed directly) starts the
development server.
"""

import os

from app import create_app

# The `app` object is what `flask --app run.py` discovers automatically.
app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=app.config["DEBUG"],
    )
