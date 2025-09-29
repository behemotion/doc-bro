#!/usr/bin/env python3
"""Migrate projects from project_registry.db to docbro.db"""

import asyncio
import sqlite3
from pathlib import Path
import json
from datetime import datetime

async def migrate_projects():
    """Migrate projects from project_registry.db to docbro.db"""

    # Source database (ProjectManager)
    source_db = Path.home() / '.local' / 'share' / 'docbro' / 'project_registry.db'
    # Target database (DatabaseManager)
    target_db = Path.home() / '.docbro' / 'docbro.db'

    if not source_db.exists():
        print("Source database not found:", source_db)
        return

    # Ensure target directory exists
    target_db.parent.mkdir(parents=True, exist_ok=True)

    # Connect to source database
    source_conn = sqlite3.connect(str(source_db))
    source_cursor = source_conn.cursor()

    # Connect to target database
    target_conn = sqlite3.connect(str(target_db))
    target_cursor = target_conn.cursor()

    try:
        # Get projects from source
        source_cursor.execute("""
            SELECT id, name, type, status, created_at, updated_at, settings_json, metadata_json
            FROM projects
        """)
        source_projects = source_cursor.fetchall()

        print(f"Found {len(source_projects)} projects in source database")

        # Check existing projects in target
        target_cursor.execute("SELECT name FROM projects")
        existing_names = {row[0] for row in target_cursor.fetchall()}
        print(f"Found {len(existing_names)} existing projects in target database")

        # Migrate each project
        migrated = 0
        skipped = 0

        for project in source_projects:
            id, name, project_type, status, created_at, updated_at, settings_json, metadata_json = project

            if name in existing_names:
                print(f"Skipping '{name}' - already exists in target")
                skipped += 1
                continue

            # Parse settings and metadata if they're JSON strings
            source_url = None
            metadata = {'type': project_type}

            if settings_json:
                try:
                    settings_dict = json.loads(settings_json)
                    # Extract source_url from settings if present
                    if 'source_url' in settings_dict:
                        source_url = settings_dict['source_url']
                    metadata['settings'] = settings_dict
                except:
                    pass

            if metadata_json:
                try:
                    metadata_dict = json.loads(metadata_json)
                    metadata.update(metadata_dict)
                except:
                    pass

            # Map status values
            status_map = {
                'active': 'created',
                'inactive': 'created',
                'archived': 'created'
            }
            mapped_status = status_map.get(status, 'created')

            # Insert into target database
            target_cursor.execute("""
                INSERT INTO projects (
                    id, name, source_url, status, crawl_depth, embedding_model,
                    chunk_size, chunk_overlap, created_at, updated_at,
                    total_pages, total_size_bytes, successful_pages, failed_pages, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                id, name, source_url, mapped_status, 2, 'mxbai-embed-large',
                1000, 100, created_at, updated_at,
                0, 0, 0, 0, json.dumps(metadata)
            ))

            print(f"Migrated project: {name}")
            migrated += 1

        # Commit changes
        target_conn.commit()

        print(f"\nMigration complete!")
        print(f"  Migrated: {migrated} projects")
        print(f"  Skipped: {skipped} projects")

    finally:
        source_conn.close()
        target_conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_projects())