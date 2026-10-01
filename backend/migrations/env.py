"""Alembic env: URL and metadata come from the p11 package."""
from alembic import context
from sqlalchemy import engine_from_config, pool

from p11.core.db import Base
from p11.core.settings import get_settings

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
target_metadata = Base.metadata


def run_offline() -> None:
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata,
                      literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_online() -> None:
    eng = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.",
                             poolclass=pool.NullPool)
    with eng.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_offline()
else:
    run_online()
