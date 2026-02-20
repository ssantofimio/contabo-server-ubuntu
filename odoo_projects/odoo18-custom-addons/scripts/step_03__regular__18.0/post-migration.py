import logging

_logger = logging.getLogger(__name__)
_logger.info("Executing post-migration.py script...")

env = env  # noqa: F821

# Write custom script here

env.cr.commit()
