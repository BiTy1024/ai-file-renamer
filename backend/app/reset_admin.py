"""CLI script to reset the admin account from environment variables.

Usage:
    python -m app.reset_admin
"""
import logging

from sqlmodel import Session

from app.core.db import engine, reset_admin

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("Resetting admin account...")
    with Session(engine) as session:
        user = reset_admin(session)
        logger.info("Admin account reset: %s (role=%s)", user.email, user.role.value)


if __name__ == "__main__":
    main()
