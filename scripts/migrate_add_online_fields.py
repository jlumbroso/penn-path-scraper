#!/usr/bin/env python3
"""
Database migration script: Add inst_method_code and campus_code fields.

This script migrates existing databases to add support for online courses
by adding the inst_method_code and campus_code fields to the courses table.

Usage:
    python scripts/migrate_add_online_fields.py <database_path>

Example:
    python scripts/migrate_add_online_fields.py ./data/courses.db
"""

import argparse
import sqlite3
import sys


def check_columns_exist(cursor: sqlite3.Cursor, table: str, columns: list[str]) -> dict[str, bool]:
    """
    Check if columns exist in a table.

    Args:
        cursor: SQLite cursor
        table: Table name
        columns: List of column names to check

    Returns:
        Dict mapping column name to whether it exists
    """
    cursor.execute(f"PRAGMA table_info({table})")
    existing_columns = {row[1] for row in cursor.fetchall()}

    return {col: col in existing_columns for col in columns}


def migrate_database(db_path: str, dry_run: bool = False) -> None:
    """
    Migrate database to add inst_method_code and campus_code fields.

    Args:
        db_path: Path to SQLite database
        dry_run: If True, only check what would be done without making changes
    """
    print(f"{'[DRY RUN] ' if dry_run else ''}Migrating database: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if courses table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='courses'")
        if not cursor.fetchone():
            print("ERROR: 'courses' table not found in database")
            sys.exit(1)

        # Check which columns need to be added
        columns_to_add = ["inst_method_code", "campus_code"]
        column_status = check_columns_exist(cursor, "courses", columns_to_add)

        print("\nColumn status:")
        for col, exists in column_status.items():
            status = "EXISTS" if exists else "MISSING"
            print(f"  - {col}: {status}")

        # Determine what needs to be done
        missing_columns = [col for col, exists in column_status.items() if not exists]

        if not missing_columns:
            print("\nDatabase already has all required columns. No migration needed.")
            return

        print(f"\nColumns to add: {', '.join(missing_columns)}")

        if dry_run:
            print("\n[DRY RUN] Would execute the following SQL commands:")
            for col in missing_columns:
                print(f"  ALTER TABLE courses ADD COLUMN {col} VARCHAR(255) NULL;")
            print("\nRun without --dry-run to apply changes.")
            return

        # Add missing columns
        print("\nAdding missing columns...")
        for col in missing_columns:
            sql = f"ALTER TABLE courses ADD COLUMN {col} VARCHAR(255) NULL"
            print(f"  Executing: {sql}")
            cursor.execute(sql)

        # Commit changes
        conn.commit()
        print("\n✓ Migration completed successfully!")

        # Count courses
        cursor.execute("SELECT COUNT(*) FROM courses")
        course_count = cursor.fetchone()[0]
        print(f"\nDatabase contains {course_count} course records.")
        print("\nNOTE: Existing courses will have NULL values for the new fields.")
        print("      Re-run the scraper to populate these fields for existing courses.")

    except sqlite3.Error as e:
        print(f"\nERROR: Database error: {e}")
        conn.rollback()
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Unexpected error: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate database to add inst_method_code and campus_code fields",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check what would be done (dry run)
  python scripts/migrate_add_online_fields.py data/courses.db --dry-run

  # Apply migration
  python scripts/migrate_add_online_fields.py data/courses.db
        """,
    )

    parser.add_argument(
        "database",
        help="Path to SQLite database file",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check what would be done without making changes",
    )

    args = parser.parse_args()

    migrate_database(args.database, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
