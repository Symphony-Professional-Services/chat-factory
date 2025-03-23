#!/usr/bin/env python

# This script fixes the vertex_ai import issue
import sys
import os
import json

def fix_llm_init():
    """Fix the __init__.py file in the chat_factory/llm directory."""
    init_file = "chat_factory/llm/__init__.py"
    
    # Read the current content
    with open(init_file, "r") as f:
        content = f.read()
    
    # Check if we need to modify the file
    if "MockLLMProvider" in content and "VertexAIProvider" not in content:
        print(f"Fixing {init_file}...")
        
        # Add direct import at the beginning
        new_content = content.replace(
            "from .mock import MockLLMProvider",
            "from .mock import MockLLMProvider\n\n# Directly import VertexAI provider\nfrom .vertex_ai import VertexAIProvider\n"
        )
        
        # Register the provider in the registry
        new_content = new_content.replace(
            "LLM_PROVIDERS: Dict[str, Type[LLMProvider]] = {\n    \"mock\": MockLLMProvider\n}",
            "LLM_PROVIDERS: Dict[str, Type[LLMProvider]] = {\n    \"mock\": MockLLMProvider,\n    \"vertex_ai\": VertexAIProvider\n}"
        )
        
        # Comment out the try/except import block to avoid warning
        start_idx = new_content.find("# Import VertexAI provider if available")
        end_idx = new_content.find("def create_llm_provider")
        
        if start_idx != -1 and end_idx != -1:
            try_block = new_content[start_idx:end_idx]
            commented_block = "# DISABLED DYNAMIC IMPORT:\n# " + try_block.replace("\n", "\n# ")
            new_content = new_content.replace(try_block, commented_block)
        
        # Write the modified content
        with open(init_file, "w") as f:
            f.write(new_content)
        
        print("Successfully fixed LLM provider imports!")
    else:
        print("No fix needed for LLM provider imports.")

if __name__ == "__main__":
    fix_llm_init()
