#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to clean up unnecessary files for git commit
"""
import os
import shutil

def remove_file(file_path):
    """Remove file if exists"""
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            print("Deleted: " + file_path)
            return True
        except Exception as e:
            print("Failed to delete " + file_path + ": " + str(e))
            return False
    else:
        print("Not found: " + file_path)
        return False

def main():
    # Frontend files to remove
    frontend_files = [
        "frontend/test_performance_improvements.py",
        "frontend/test_login_redirect.py", 
        "frontend/test_login_api_consistency.py",
        "frontend/test_auth_token.py",
        "frontend/test_auth_loop_fix.py",
        "frontend/debug_login.py",
        "frontend/browser_test.html",
        "frontend/fix_cors_and_test.html",
        "frontend/localStorage_check.html",
        "frontend/test-auth-loop-fix.html",
        "frontend/test-infinite-loop-fix.html",
        "frontend/typescript-errors.txt",
        "frontend/package.json.backup",
        "frontend/next.config.js.backup",
        "frontend/tsconfig.json.backup"
    ]
    
    # Backend files to remove
    backend_files = [
        "backend/test_secret_key.py",
        "backend/test_auth_fix.py"
    ]
    
    # Root files to remove
    root_files = [
        "clear-auth.js"
    ]
    
    print("Starting cleanup of unnecessary files...\n")
    
    total_removed = 0
    
    # Remove frontend files
    print("Deleting Frontend files:")
    for file_path in frontend_files:
        if remove_file(file_path):
            total_removed += 1
    print()
    
    # Remove backend files
    print("Deleting Backend files:")
    for file_path in backend_files:
        if remove_file(file_path):
            total_removed += 1
    print()
    
    # Remove root files
    print("Deleting Root files:")
    for file_path in root_files:
        if remove_file(file_path):
            total_removed += 1
    print()
    
    print("Cleanup completed! Removed " + str(total_removed) + " files")

if __name__ == "__main__":
    main()