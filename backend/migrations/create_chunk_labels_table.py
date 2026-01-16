"""
Migration script to create chunk_labels table.

Run this script to add the chunk labeling system to your database.

Usage:
    python migrations/create_chunk_labels_table.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.database import Base, engine, init_db
from app.core.database import test_database_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Create chunk_labels table and any other missing tables."""
    logger.info("=" * 80)
    logger.info("Chunk Labels Table Migration")
    logger.info("=" * 80)

    # Test connection
    logger.info("Testing database connection...")
    success, error_msg = test_database_connection(engine)

    if not success:
        logger.error("Database connection failed:")
        logger.error(error_msg)
        logger.error("Cannot proceed with migration. Please check your database configuration.")
        return False

    logger.info("✓ Database connection successful")

    # Create tables
    logger.info("Creating tables...")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✓ Tables created successfully")

        # List all tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        logger.info(f"\nDatabase now contains {len(tables)} tables:")
        for table in sorted(tables):
            logger.info(f"  - {table}")

        if 'chunk_labels' in tables:
            logger.info("\n✓ chunk_labels table is ready")
        else:
            logger.warning("\n⚠ chunk_labels table was not created")
            return False

        logger.info("\n" + "=" * 80)
        logger.info("Migration completed successfully!")
        logger.info("=" * 80)
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
