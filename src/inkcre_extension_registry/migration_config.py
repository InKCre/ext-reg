"""Configuration entry point for the Tortoise migration CLI."""

import os

from .service.settings import database_config

TORTOISE_ORM = database_config(
    os.environ.get("MIGRATION_DATABASE_URL") or os.environ["DATABASE_URL"]
)
