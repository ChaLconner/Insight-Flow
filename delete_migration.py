#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to delete migration files
"""
import os

# List of migration files to delete
migration_files = [
    'backend/migrate_role_field_postgresql.py',
    'backend/migrate_role_field.py', 
    'backend/reset_admin_password.py'
]

print('Deleting migration files...')
total_removed = 0

for file_path in migration_files:
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print('Deleted: ' + file_path)
            total_removed += 1
        except Exception as e:
            print('Failed to delete ' + file_path + ': ' + str(e))
    else:
        print('Not found: ' + file_path)

print('Cleanup completed! Removed ' + str(total_removed) + ' migration files')