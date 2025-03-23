#!/usr/bin/env python3
"""
Script to help set up and verify Google Cloud credentials for Chat Factory.

This script:
1. Verifies if credentials file exists
2. Tests authentication with Google Cloud
3. Provides guidance on setting up credentials

Usage:
    python setup_credentials.py [--creds-file PATH] [--project-id PROJECT_ID]
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Google Cloud Credentials Setup Helper")
    parser.add_argument(
        "--creds-file", 
        default="google-service-account.json",
        help="Path to Google Cloud service account JSON file (default: google-service-account.json)"
    )
    parser.add_argument(
        "--project-id",
        help="Google Cloud project ID (extracted from credentials if not provided)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check credentials, don't attempt to fix or offer guidance"
    )
    return parser.parse_args()


def print_section(title, color="blue"):
    """Print a formatted section title."""
    colors = {
        "red": "\033[0;31m",
        "green": "\033[0;32m",
        "yellow": "\033[1;33m",
        "blue": "\033[0;34m",
        "reset": "\033[0m",
    }
    
    print(f"\n{colors[color]}{'=' * 50}")
    print(f" {title}")
    print(f"{'=' * 50}{colors['reset']}")


def check_credentials_file(creds_path):
    """Check if credentials file exists and is valid."""
    print_section("Checking credentials file")
    
    creds_path = Path(creds_path)
    
    # Check if file exists
    if not creds_path.exists():
        print(f"❌ Credentials file not found: {creds_path}")
        return False, None
    
    # Check file permissions
    if not os.access(creds_path, os.R_OK):
        print(f"❌ Credentials file exists but is not readable: {creds_path}")
        return False, None
    
    # Check if it's a valid JSON
    try:
        with open(creds_path, 'r') as f:
            creds_data = json.load(f)
        
        # Verify it looks like a service account key
        if 'type' not in creds_data or creds_data['type'] != 'service_account':
            print(f"❌ File exists but doesn't appear to be a service account key: {creds_path}")
            return False, None
        
        project_id = creds_data.get('project_id')
        if not project_id:
            print(f"⚠️ Service account key doesn't contain a project_id: {creds_path}")
            return True, None
        
        print(f"✅ Valid service account key found: {creds_path}")
        print(f"   Project ID: {project_id}")
        return True, project_id
        
    except json.JSONDecodeError:
        print(f"❌ File exists but is not valid JSON: {creds_path}")
        return False, None
    except Exception as e:
        print(f"❌ Error reading credentials file: {str(e)}")
        return False, None


def test_authentication(creds_path, project_id):
    """Test authentication with Google Cloud."""
    print_section("Testing Google Cloud Authentication")
    
    # Set environment variable for credentials
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(Path(creds_path).resolve())
    
    # Try a simple Google Cloud operation
    try:
        # Check if gcloud CLI is installed
        try:
            subprocess.run(
                ["gcloud", "--version"], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                check=True
            )
            has_gcloud = True
        except (subprocess.SubprocessError, FileNotFoundError):
            has_gcloud = False
        
        if has_gcloud:
            # Test authentication with gcloud
            result = subprocess.run(
                ["gcloud", "auth", "activate-service-account", "--key-file", os.environ["GOOGLE_APPLICATION_CREDENTIALS"]],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                print(f"❌ Authentication failed with gcloud: {result.stderr}")
                return False
            
            # Test listing models
            if project_id:
                result = subprocess.run(
                    ["gcloud", "ai", "models", "list", "--region=us-central1", f"--project={project_id}"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if result.returncode != 0:
                    print(f"❌ Failed to list AI models: {result.stderr}")
                    print("  This may indicate missing Vertex AI permissions.")
                    return False
                
                print("✅ Successfully authenticated with Google Cloud")
                print("✅ Successfully listed AI models")
                return True
        
        # If gcloud isn't available or project_id wasn't provided, try Python API
        print("Attempting authentication via Python API...")
        
        # Try importing required packages
        try:
            from google.cloud import aiplatform
            have_api = True
        except ImportError:
            have_api = False
            print("❌ Google Cloud packages not installed. Installing...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "google-cloud-aiplatform"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            try:
                from google.cloud import aiplatform
                have_api = True
                print("✅ Successfully installed Google Cloud packages")
            except ImportError:
                print("❌ Failed to install Google Cloud packages")
        
        if have_api and project_id:
            try:
                # Initialize the AI Platform client
                aiplatform.init(project=project_id, location="us-central1")
                
                # List models (this will verify authentication)
                models = aiplatform.Model.list()
                
                print("✅ Successfully authenticated with Google Cloud")
                print(f"✅ Successfully connected to project: {project_id}")
                return True
            except Exception as e:
                print(f"❌ Error connecting to Google Cloud: {str(e)}")
                return False
        elif have_api:
            print("⚠️ Project ID not provided, skipping API connectivity test")
            return True
    
    except Exception as e:
        print(f"❌ Error testing authentication: {str(e)}")
        return False


def provide_guidance():
    """Provide guidance on setting up credentials."""
    print_section("Guidance on Setting Up Google Cloud Credentials", "yellow")
    
    print("To use Chat Factory with Vertex AI, you need a Google Cloud service account key.")
    print("\n1. Create a service account in the Google Cloud Console:")
    print("   - Go to: https://console.cloud.google.com/iam-admin/serviceaccounts")
    print("   - Click 'Create Service Account'")
    print("   - Give it a name like 'chat-factory-service-account'")
    print("   - Add these roles:")
    print("     * Vertex AI User")
    print("     * Storage Object Viewer (if reading from GCS)")
    
    print("\n2. Create a key for the service account:")
    print("   - Click on the service account you created")
    print("   - Go to the 'Keys' tab")
    print("   - Click 'Add Key' > 'Create new key'")
    print("   - Choose JSON format")
    print("   - Download the key file")
    
    print("\n3. Place the key file in your project directory:")
    print("   - Rename it to 'google-service-account.json'")
    print("   - Or use a different name and specify it with GOOGLE_APPLICATION_CREDENTIALS")
    
    print("\n4. Test your credentials:")
    print("   - Run this script again: python setup_credentials.py")
    print("   - Or run: python setup_credentials.py --creds-file path/to/your-key.json")
    
    print("\n5. Using with Docker:")
    print("   - Mount your credentials file as a volume:")
    print("   - docker run -v /path/to/your-key.json:/app/google-service-account.json ...")


def check_docker_setup():
    """Check Docker setup."""
    print_section("Checking Docker Setup")
    
    # Check if Docker is installed
    try:
        subprocess.run(
            ["docker", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        print("✅ Docker is installed")
    except (subprocess.SubprocessError, FileNotFoundError):
        print("❌ Docker is not installed or not in PATH")
        print("   To install Docker, visit: https://docs.docker.com/get-docker/")
        return
    
    # Check if Dockerfile exists
    if not Path("Dockerfile").exists():
        print("❌ Dockerfile not found in current directory")
        return
    
    print("✅ Dockerfile found")
    
    # Provide Docker run commands
    print("\nTo run Chat Factory with Docker:")
    print("\n1. Build the Docker image:")
    print("   docker build -t chat-factory .")
    
    print("\n2. Run with mock provider (no credentials needed):")
    print("   docker run -it --rm -v $(pwd):/app chat-factory")
    
    print("\n3. Run with Vertex AI (requires credentials):")
    print("   docker run -it --rm \\")
    print("     -v $(pwd):/app \\")
    print("     -v /path/to/your-key.json:/app/google-service-account.json \\")
    print("     -e USE_MOCK_PROVIDER=false \\")
    print("     chat-factory")


def main():
    """Main function."""
    args = parse_args()
    
    print_section("Chat Factory Credentials Setup Tool", "green")
    print(f"Checking credentials file: {args.creds_file}")
    
    # Check credentials file
    valid_file, project_id = check_credentials_file(args.creds_file)
    
    # Use provided project ID if given
    project_id = args.project_id or project_id
    
    # Test authentication if we have valid credentials
    auth_success = False
    if valid_file:
        auth_success = test_authentication(args.creds_file, project_id)
    
    # Print summary
    print_section("Summary", "yellow")
    
    if valid_file and auth_success:
        print("✅ Credentials file is valid and authentication successful!")
        print(f"✅ You can now use Vertex AI with project: {project_id}")
        
        print("\nTo use these credentials:")
        print(f"1. Set environment variable: export GOOGLE_APPLICATION_CREDENTIALS={os.path.abspath(args.creds_file)}")
        print("2. Or run with Docker: docker run -v $PWD:/app " + 
              f"-v {os.path.abspath(args.creds_file)}:/app/google-service-account.json " +
              "-e USE_MOCK_PROVIDER=false chat-factory")
        
    elif valid_file:
        print("⚠️ Credentials file is valid but authentication failed.")
        print("   This might indicate missing permissions or project configuration issues.")
    else:
        print("❌ Valid credentials file not found.")
    
    # Check Docker setup
    check_docker_setup()
    
    # Provide guidance if requested or if there were issues
    if not args.check_only and (not valid_file or not auth_success):
        provide_guidance()


if __name__ == "__main__":
    main()