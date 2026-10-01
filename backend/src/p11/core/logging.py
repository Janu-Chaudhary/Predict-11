"""Structured logging (JSON in prod, pretty console in dev)."""

from __future__ import annotations

import logging

import structlog

from .settings import get_settings


def configure() -> None:
    dev = get_settings().env == "dev"
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer() if dev else structlog.processors.JSONRenderer(),
        ],
    )


log = structlog.get_logger()
