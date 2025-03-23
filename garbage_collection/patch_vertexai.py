#!/usr/bin/env python
"""
Script to patch the vertex_ai.py file to fix import issues.
"""

import sys
import os

def patch_vertexai():
    """
    Patch the vertex_ai.py file to handle import errors better.
    """
    vertex_ai_file = "chat_factory/llm/vertex_ai.py"
    
    # Read the current content
    with open(vertex_ai_file, "r") as f:
        content = f.read()
    
    # Check if we need to modify the file
    if "import vertexai" not in content and "# First try to import" in content:
        print(f"Adding explicit import to {vertex_ai_file}...")
        
        # Replace the import section with direct imports
        old_imports = "# First try to import from the new GenAI SDK\ntry:\n    from google import genai\n    from google.genai.types import HttpOptions\n    USING_GENAI_SDK = True\nexcept ImportError:\n    # Fall back to the older Vertex AI SDK\n    try:\n        import vertexai\n        from vertexai.preview.generative_models import GenerativeModel, GenerationConfig\n        USING_GENAI_SDK = False\n    except ImportError:\n        raise ImportError(\"Neither google-genai nor vertexai package is installed. Please install at least one.\")"
        
        new_imports = """# Import both SDKs directly
import vertexai
from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
from google import genai
from google.genai.types import HttpOptions

# Assume GenAI SDK is available until proven otherwise
USING_GENAI_SDK = True
try:
    # Test GenAI SDK
    _ = genai.GenerativeModel
except (ImportError, AttributeError):
    USING_GENAI_SDK = False"""
        
        new_content = content.replace(old_imports, new_imports)
        
        # If the content hasn't changed, check other possible import patterns
        if new_content == content:
            # Try to find the import section by looking for common imports
            import_start = content.find('"""')
            if import_start != -1:
                import_start = content.find('"""', import_start + 3)
                if import_start != -1:
                    import_start = import_start + 3
                    
                    # Find where imports end (usually at class definition)
                    import_end = content.find('class VertexAIProvider')
                    if import_end != -1:
                        # Get the import section
                        import_section = content[import_start:import_end].strip()
                        
                        # Create the new imports
                        new_import_section = import_section + "\n\n" + "# Explicitly import vertexai\nimport vertexai\n"
                        
                        # Replace in content
                        new_content = content.replace(import_section, new_import_section)
        
        # Write the modified content
        if new_content != content:
            with open(vertex_ai_file, "w") as f:
                f.write(new_content)
            
            print("Successfully patched VertexAI implementation!")
            return True
        else:
            print("No modifications needed for vertex_ai.py (imports not found).")
            return False
    else:
        print("No patching needed for vertex_ai.py.")
        return False

if __name__ == "__main__":
    success = patch_vertexai()
    sys.exit(0)