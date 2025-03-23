#!/bin/bash

# Create a test script to check credentials inside the container
cat > check_creds.py << 'EOF'
#!/usr/bin/env python3
import os
import json
import sys

print("=" * 50)
print("Google Cloud Credentials Test Inside Docker")
print("=" * 50)

# Check credentials path
creds_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
print(f"GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")

# Check if file exists
if not os.path.exists(creds_path):
    print(f"ERROR: File not found: {creds_path}")
    sys.exit(1)

# Check file permissions
print(f"File permissions: {oct(os.stat(creds_path).st_mode)[-3:]}")

# Try to read the credentials
try:
    with open(creds_path, 'r') as f:
        creds = json.load(f)
    
    if 'type' in creds and creds['type'] == 'service_account':
        print(f"✓ Valid service account with project_id: {creds.get('project_id')}")
    else:
        print("✗ Not a valid service account key file")
except Exception as e:
    print(f"ERROR reading credentials: {str(e)}")

# Check required packages
print("\nChecking required packages:")
try:
    import google.cloud.aiplatform
    print("✓ google-cloud-aiplatform installed")
except ImportError:
    print("✗ google-cloud-aiplatform NOT installed")

try:
    import vertexai
    print("✓ vertexai installed")
except ImportError:
    print("✗ vertexai NOT installed")

try:
    import google.genai
    print("✓ google-genai installed")
except ImportError:
    print("✗ google-genai NOT installed")

# Try quick authentication test
print("\nTesting authentication:")
try:
    from google.cloud import storage
    storage_client = storage.Client()
    print("✓ Successfully authenticated with Storage")
except Exception as e:
    print(f"✗ Storage authentication failed: {str(e)}")

try:
    from google.cloud import aiplatform
    aiplatform.init(project=creds.get('project_id'), location="us-central1")
    print("✓ Successfully initialized AI Platform")
except Exception as e:
    print(f"✗ AI Platform initialization failed: {str(e)}")
EOF

chmod +x check_creds.py

# Run the test in Docker
echo "Running credential test in Docker container..."
docker run --rm \
  -v "$(pwd)/check_creds.py:/app/check_creds.py" \
  -v "$(pwd)/google-service-account.json:/app/google-service-account.json" \
  --entrypoint python \
  chat-factory \
  /app/check_creds.py

# Clean up
rm check_creds.py