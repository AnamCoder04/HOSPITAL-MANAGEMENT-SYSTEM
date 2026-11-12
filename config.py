"""Application configuration.

One class per environment, selected with the FLASK_CONFIG environment
variable. Secrets come from the environment (loaded from .env by
python-dotenv) and never from source code.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = the folder that contains this file.
BASE_DIR = Path(__file__).resolve().parent

# Load .env into os.environ before the classes below are evaluated.
load_dotenv(BASE_DIR / ".env")


class Config:
    """Settings shared by every environment."""

    # --- Core -----------------------------------------------------------
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-insecure-secret-key")
    HOSPITAL_NAME = "MediCare HMS"
    HOSPITAL_TAGLINE = "Modern, connected hospital care"

    # --- Database -------------------------------------------------------
    # A relative SQLite path is resolved inside Flask's instance/ folder,
    # i.e. sqlite:///hms.sqlite3 -> <project>/instance/hms.sqlite3
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///hms.sqlite3")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # --- Security -------------------------------------------------------
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_HTTPONLY = True
    WTF_CSRF_TIME_LIMIT = None  # token valid for the whole session

    # --- Business rules (used from Task 3 onwards) ----------------------
    ITEMS_PER_PAGE = 10
    APPOINTMENT_WINDOW_DAYS = 7

    # --- Seeded administrator (created on first run, Task 3) ------------
    ADMIN_NAME = os.environ.get("ADMIN_NAME", "System Administrator")
    # NOTE: use a normal domain here. Addresses on reserved domains such as
    # .local / .test / .example are rejected by strict e-mail validators.
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@medicare-hms.com")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@12345")


class DevelopmentConfig(Config):
    """Local development: debug on, reloader on."""

    DEBUG = True
    TEMPLATES_AUTO_RELOAD = True


class TestingConfig(Config):
    """Used by automated checks: in-memory database, CSRF off."""

    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    SECRET_KEY = "testing-secret-key"


class ProductionConfig(Config):
    """Deployment: debug off, require an explicit secret key."""

    DEBUG = False
    SESSION_COOKIE_SECURE = True


CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name: str | None = None) -> type[Config]:
    """Return the config class for FLASK_CONFIG / the given name."""
    key = (name or os.environ.get("FLASK_CONFIG") or "development").lower()
    return CONFIG_MAP.get(key, DevelopmentConfig)
