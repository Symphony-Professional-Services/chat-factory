#!/usr/bin/env python3
"""
Simple script to test Google Cloud credentials.
"""

import os
import sys
import json

def main():
    """Main function to test credentials."""
    # Check if GOOGLE_APPLICATION_CREDENTIALS is set
    creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
    if not creds_path:
        print("ERROR: GOOGLE_APPLICATION_CREDENTIALS environment variable is not set.")
        print("Set it to the path of your service account key file.")
        return False
    
    print(f"Using credentials from: {creds_path}")
    
    # Check if the file exists
    if not os.path.exists(creds_path):
        print(f"ERROR: Credentials file not found at: {creds_path}")
        return False
    
    print(f"Credentials file exists: {creds_path}")
    
    # Try to read the JSON file
    try:
        with open(creds_path, 'r') as f:
            creds_data = json.load(f)
        
        # Check if it's a valid service account file
        if 'type' not in creds_data or creds_data['type'] != 'service_account':
            print(f"ERROR: File is not a valid service account key.")
            return False
        
        project_id = creds_data.get('project_id')
        if not project_id:
            print(f"WARNING: Service account key doesn't contain a project_id")
        else:
            print(f"Project ID: {project_id}")
        
        # Check required fields
        required_fields = ['private_key', 'client_email']
        missing_fields = [field for field in required_fields if field not in creds_data]
        
        if missing_fields:
            print(f"ERROR: Service account key is missing required fields: {', '.join(missing_fields)}")
            return False
        
        print("Service account key is valid!")
        
        # Try importing required packages
        try:
            print("\nTesting Google Cloud packages...")
            
            try:
                import google.cloud.aiplatform
                print("✓ google-cloud-aiplatform package is installed")
            except ImportError:
                print("✗ google-cloud-aiplatform package is NOT installed")
            
            try:
                import vertexai
                print("✓ vertexai package is installed")
            except ImportError:
                print("✗ vertexai package is NOT installed")
            
            try:
                import google.genai
                print("✓ google-genai package is installed")
            except ImportError:
                print("✗ google-genai package is NOT installed")
            
            # Try authenticating
            print("\nTesting authentication...")
            
            # Try using different client libraries to test authentication
            try:
                from google.cloud import storage
                storage_client = storage.Client()
                print("✓ Successfully authenticated with Google Cloud Storage")
            except Exception as e:
                print(f"✗ Failed to authenticate with Google Cloud Storage: {str(e)}")
            
            try:
                from google.cloud import aiplatform
                aiplatform.init(project=project_id, location="us-central1")
                print("✓ Successfully initialized AI Platform")
            except Exception as e:
                print(f"✗ Failed to initialize AI Platform: {str(e)}")
            
            return True
        
        except Exception as e:
            print(f"Error testing authentication: {str(e)}")
            return False
    
    except json.JSONDecodeError:
        print(f"ERROR: File exists but is not valid JSON: {creds_path}")
        return False
    except Exception as e:
        print(f"ERROR: Failed to read credentials file: {str(e)}")
        return False

if __name__ == "__main__":
    # Set credentials path from argument or use default
    if len(sys.argv) > 1:
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = sys.argv[1]
    
    print("Google Cloud Credentials Tester")
    print("=" * 40)
    success = main()
    
    if success:
        print("\nSUCCESS: Credentials are valid and working!")
        sys.exit(0)
    else:
        print("\nFAILED: Credentials test encountered errors.")
        sys.exit(1)