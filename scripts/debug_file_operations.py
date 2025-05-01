#!/usr/bin/env python

"""
Debug script to check file operations and permissions.
This script will attempt to:
1. Create directories
2. Write test files
3. Print permission information
"""

import os
import json
import pathlib
from datetime import datetime
import sys
import subprocess

def main():
    print("Starting file operations debugging script")
    
    # Get current user info
    try:
        current_user = os.getlogin()
    except:
        current_user = "unknown"
    
    print(f"Current user: {current_user}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Check if we can write to the current directory
    test_file_path = "test_write_permissions.txt"
    try:
        with open(test_file_path, "w") as f:
            f.write("Test write access")
        print(f"Successfully wrote to {test_file_path}")
        os.remove(test_file_path)
        print(f"Successfully removed {test_file_path}")
    except Exception as e:
        print(f"Error writing to current directory: {e}")
    
    # Check synthetic_data directory permissions
    synthetic_dir = pathlib.Path("synthetic_data")
    print(f"\nChecking synthetic_data directory: {synthetic_dir.absolute()}")
    
    if not synthetic_dir.exists():
        print(f"Directory {synthetic_dir} doesn't exist, creating it")
        try:
            synthetic_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created directory {synthetic_dir}")
        except Exception as e:
            print(f"Error creating directory {synthetic_dir}: {e}")
    
    # Get directory info
    try:
        dir_stat = os.stat(synthetic_dir)
        print(f"Directory owner (uid): {dir_stat.st_uid}")
        print(f"Directory group (gid): {dir_stat.st_gid}")
        print(f"Directory permissions: {oct(dir_stat.st_mode)}")
    except Exception as e:
        print(f"Error getting directory info: {e}")
    
    # List contents of synthetic_data
    print("\nContents of synthetic_data directory:")
    try:
        for item in synthetic_dir.iterdir():
            item_stat = os.stat(item)
            print(f"- {item.name} (owner uid: {item_stat.st_uid}, perms: {oct(item_stat.st_mode)})")
    except Exception as e:
        print(f"Error listing directory contents: {e}")
    
    # Create a test run directory
    run_id = f"debug_run_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}"
    run_dir = synthetic_dir / run_id
    
    print(f"\nCreating test run directory: {run_dir}")
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created directory {run_dir}")
    except Exception as e:
        print(f"Error creating run directory: {e}")
        return
    
    # Try to create a test advisor directory
    advisor_dir = run_dir / "TestAdvisor"
    try:
        advisor_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created advisor directory {advisor_dir}")
    except Exception as e:
        print(f"Error creating advisor directory: {e}")
        return
    
    # Try to write a test conversation file
    test_conv_file = advisor_dir / "TestClient.json"
    test_data = {
        "version": "5",
        "advisor": "TestAdvisor",
        "client": "TestClient",
        "conversations": [
            {
                "conversation_id": "test_123",
                "timestamp": datetime.now().isoformat(),
                "category": "Test Category",
                "topic": "Test Topic.Test Subtopic",
                "lines": [
                    {"speaker": "advisor", "text": "Hello, how can I help you?"},
                    {"speaker": "client", "text": "Just testing file operations."}
                ]
            }
        ]
    }
    
    try:
        with open(test_conv_file, 'w') as f:
            json.dump(test_data, f, indent=4)
        print(f"Successfully wrote test conversation file to {test_conv_file}")
    except Exception as e:
        print(f"Error writing test conversation file: {e}")
    
    # Try to list files in the test directory
    print("\nContents of test run directory:")
    try:
        for item in run_dir.glob("**/*"):
            if item.is_file():
                item_stat = os.stat(item)
                file_size = os.path.getsize(item)
                print(f"- {item.relative_to(run_dir)} (size: {file_size} bytes, owner uid: {item_stat.st_uid})")
    except Exception as e:
        print(f"Error listing test directory contents: {e}")
    
    # Try to read the file back
    if test_conv_file.exists():
        try:
            with open(test_conv_file, 'r') as f:
                content = json.load(f)
            print(f"Successfully read test file, found {len(content['conversations'])} conversations")
        except Exception as e:
            print(f"Error reading test file: {e}")
    
    print("\nDebug script completed")

if __name__ == "__main__":
    main()
