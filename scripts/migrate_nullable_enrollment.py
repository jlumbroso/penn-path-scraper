#!/usr/bin/env python3
"""
Database migration script: Make enrollment fields nullable.

This script migrates existing databases to allow NULL values in enrollment
fields (max_enrollment, seats_available, enrolled). This is required to handle
courses with missing seats data (cancelled, full, or historical courses).

Background:
- Penn's API returns empty seats HTML for cancelled/full/historical courses
- ~19,710 sections affected (primarily pre-Spring 2024)
- We use NULL instead of fabricating 0 or -1 values

Usage:
    python scripts/migrate_nullable_enrollment.py <database_path>

Example:
    python scripts/migrate_nullable_enrollment.py ./data/courses.db
"""

import argparse
import sqlite3
import sys


def check_column_nullable(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """
    Check if a column allows NULL values.

    Args:
        cursor: SQLite cursor
        table: Table name
        column: Column name

    Returns:
        True if column allows NULL, False otherwise
    """
    cursor.execute(f"PRAGMA table_info({table})")
    for row in cursor.fetchall():
        col_name = row[1]
        not_null = row[3]  # 1 if NOT NULL, 0 otherwise
        if col_name == column:
            return not_null == 0

    return False  # Column doesn't exist


def migrate_database(db_path: str, dry_run: bool = False) -> None:
    """
    Migrate database to make enrollment fields nullable.

    SQLite doesn't support ALTER COLUMN, so we need to:
    1. Create new table with nullable fields
    2. Copy data
    3. Drop old table
    4. Rename new table

    Args:
        db_path: Path to SQLite database
        dry_run: If True, only check what would be done
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

        # Check current schema
        columns_to_check = ["max_enrollment", "seats_available", "enrolled"]
        nullable_status = {
            col: check_column_nullable(cursor, "courses", col)
            for col in columns_to_check
        }

        print("\nCurrent schema:")
        for col, is_nullable in nullable_status.items():
            status = "NULLABLE" if is_nullable else "NOT NULL"
            print(f"  - {col}: {status}")

        # Check if migration needed
        if all(nullable_status.values()):
            print("\nDatabase already has nullable enrollment fields. No migration needed.")
            return

        print(f"\n{'[DRY RUN] ' if dry_run else ''}Migration required.")

        if dry_run:
            print("\n[DRY RUN] Would execute the following steps:")
            print("  1. Get current schema of 'courses' table")
            print("  2. Create 'courses_new' with nullable enrollment fields")
            print("  3. Copy all data from 'courses' to 'courses_new'")
            print("  4. Drop 'courses' table")
            print("  5. Rename 'courses_new' to 'courses'")
            print("\nRun without --dry-run to apply changes.")
            return

        # Get full table schema
        cursor.execute("PRAGMA table_info(courses)")
        original_schema = cursor.fetchall()

        # Count records before migration
        cursor.execute("SELECT COUNT(*) FROM courses")
        record_count = cursor.fetchone()[0]
        print(f"\nMigrating {record_count} course records...")

        # Build CREATE TABLE statement for new table
        new_columns = []
        for col_info in original_schema:
            col_id, col_name, col_type, not_null, default_val, is_pk = col_info

            # Make enrollment fields nullable
            if col_name in columns_to_check:
                not_null = 0  # Allow NULL

            col_def = f"{col_name} {col_type}"
            if is_pk:
                col_def += " PRIMARY KEY"
            elif not_null:
                col_def += " NOT NULL"
            if default_val is not None:
                col_def += f" DEFAULT {default_val}"

            new_columns.append(col_def)

        # Get foreign key definitions
        cursor.execute("PRAGMA foreign_key_list(courses)")
        fk_list = cursor.fetchall()

        for fk in fk_list:
            fk_id, seq, ref_table, from_col, to_col, on_update, on_delete, match = fk
            fk_def = f"FOREIGN KEY ({from_col}) REFERENCES {ref_table}({to_col})"
            if on_delete:
                fk_def += f" ON DELETE {on_delete}"
            if on_update:
                fk_def += f" ON UPDATE {on_update}"
            new_columns.append(fk_def)

        create_sql = f"CREATE TABLE courses_new (\n  {',\n  '.join(new_columns)}\n)"

        print("\nExecuting migration steps:")
        print("  1. Creating courses_new table...")
        cursor.execute(create_sql)

        print("  2. Copying data...")
        column_names = [col[1] for col in original_schema]
        columns_str = ", ".join(column_names)
        cursor.execute(f"INSERT INTO courses_new SELECT {columns_str} FROM courses")

        print("  3. Dropping old courses table...")
        cursor.execute("DROP TABLE courses")

        print("  4. Renaming courses_new to courses...")
        cursor.execute("ALTER TABLE courses_new RENAME TO courses")

        # Recreate indexes
        print("  5. Recreating indexes...")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_courses_code ON courses(code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_courses_term_code ON courses(term_id, code)")

        # Commit changes
        conn.commit()

        # Verify migration
        cursor.execute("SELECT COUNT(*) FROM courses")
        new_count = cursor.fetchone()[0]

        if new_count != record_count:
            raise Exception(f"Record count mismatch: {record_count} → {new_count}")

        print("\n✓ Migration completed successfully!")
        print(f"\nVerification:")
        print(f"  - Records migrated: {new_count}")

        # Check new schema
        print(f"  - Enrollment fields now nullable:")
        for col in columns_to_check:
            is_nullable = check_column_nullable(cursor, "courses", col)
            status = "✓" if is_nullable else "✗"
            print(f"    {status} {col}")

        print("\nNOTE: Run scraper to populate enrollment data for existing courses.")

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
        description="Migrate database to make enrollment fields nullable",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Background:
Penn's API returns empty seats HTML for:
  - Cancelled courses (status="Canceled")
  - Full courses (status="Full")
  - Historical courses (pre-Spring 2024)

This affects ~19,710 sections across historical terms. We use NULL instead of
fabricating 0 or -1 values to maintain data integrity.

Examples:
  # Check what would be done (dry run)
  python scripts/migrate_nullable_enrollment.py data/courses.db --dry-run

  # Apply migration
  python scripts/migrate_nullable_enrollment.py data/courses.db
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
