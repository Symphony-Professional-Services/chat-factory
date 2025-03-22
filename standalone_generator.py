#!/usr/bin/env python

"""
Standalone script for generating synthetic conversations with proper company counts from taxonomy.
This script avoids permission issues by implementing the key functionality directly
without importing from the main module.
"""

import asyncio
import json
import os
import sys
import random
import uuid
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Constants (copied from config.py to avoid import issues)
NUM_CONVERSATIONS = 20
MIN_MESSAGES = 5
MAX_MESSAGES = 15
TAXONOMY_FILE = "taxonomies/taxonomy.json"
OUTPUT_DIR = "synthetic_data"
ADVISOR_NAMES = ["Alice Johnson", "Bob Smith", "Carol White", "David Lee", "Emma Brown"]
CLIENT_NAMES = ["Frank", "Grace", "Henry", "Isabella", "Jack", "Diana"]
JSON_VERSION = "1.0"

# Models for conversation data
class Message:
    def __init__(self, speaker: str, text: str):
        self.speaker = speaker
        self.text = text
    
    def to_dict(self):
        return {"speaker": self.speaker, "text": self.text}

class SingleConversation:
    def __init__(self, conversation_id: str, topic: str, subtopic: str, messages: List[Message], 
                 company_mentions: Optional[List[str]] = None):
        self.conversation_id = conversation_id
        self.topic = topic
        self.subtopic = subtopic
        self.messages = messages
        self.company_mentions = company_mentions or []
    
    def to_dict(self):
        return {
            "conversation_id": self.conversation_id,
            "topic": self.topic,
            "subtopic": self.subtopic,
            "messages": [msg.to_dict() for msg in self.messages],
            "company_mentions": self.company_mentions
        }

class ConversationFile:
    def __init__(self, version: str, advisor: str, client: str, conversations: List[SingleConversation]):
        self.version = version
        self.advisor = advisor
        self.client = client
        self.conversations = conversations
    
    def to_dict(self):
        return {
            "version": self.version,
            "advisor": self.advisor,
            "client": self.client,
            "conversations": [conv.to_dict() for conv in self.conversations]
        }

class StandaloneGenerator:
    def __init__(self):
        self.num_conversations = NUM_CONVERSATIONS
        self.min_messages = MIN_MESSAGES
        self.max_messages = MAX_MESSAGES
        self.taxonomy_file = TAXONOMY_FILE
        self.output_dir_base = Path(OUTPUT_DIR)
        self.advisor_names = ADVISOR_NAMES
        self.client_names = CLIENT_NAMES
        self.json_version = JSON_VERSION
        
        # Generate a unique run ID
        self.run_id = f"run_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}"
        self.output_dir = self.setup_output_directory()
        
        # Load taxonomy
        self.taxonomy = self.load_taxonomy()
        
        # Conversation buffer to collect conversations
        self.conversation_buffer = {}
        
        print(f"StandaloneGenerator initialized with run_id: {self.run_id}")
    
    def load_taxonomy(self) -> Dict:
        """Load the taxonomy from the JSON file."""
        try:
            with open(self.taxonomy_file, 'r', encoding='utf-8') as f:
                taxonomy = json.load(f)
            print(f"Successfully loaded taxonomy from {self.taxonomy_file}")
            conversation_types = taxonomy.get('conversation_types', {})
            print(f"Found {len(conversation_types)} conversation types")
            return taxonomy
        except Exception as e:
            print(f"Error loading taxonomy: {e}")
            return {"conversation_types": {}}
    
    def setup_output_directory(self) -> Path:
        """Sets up the output directory with run_id as parent."""
        try:
            run_output_dir = self.output_dir_base / self.run_id
            run_output_dir.mkdir(parents=True, exist_ok=True)
            print(f"Output directory set to: {run_output_dir}")
        except Exception as e:
            print(f"Error setting up output directory: {e}")
            raise
        return run_output_dir
    
    def select_conversation_type(self, index=None) -> str:
        """Select a conversation type from the taxonomy."""
        conversation_types = list(self.taxonomy.get("conversation_types", {}).keys())
        if not conversation_types:
            print("Warning: No conversation types found in taxonomy. Using default type.")
            return "Default Type"
        
        if index is not None and 0 <= index < len(conversation_types):
            return conversation_types[index]
        
        return random.choice(conversation_types)
    
    def get_company_count_for_type(self, conversation_type: str) -> int:
        """Get the number of companies to mention for a conversation type from taxonomy."""
        conversation_types = self.taxonomy.get("conversation_types", {})
        type_info = conversation_types.get(conversation_type, {})
        company_count_options = type_info.get("company_count_options", [1])
        return random.choice(company_count_options)
    
    def select_advisors_clients(self, index=None) -> Tuple[str, str]:
        """Select an advisor and client pair."""
        if index is not None and 0 <= index < len(self.advisor_names) * len(self.client_names):
            advisor_idx = index % len(self.advisor_names)
            client_idx = (index // len(self.advisor_names)) % len(self.client_names)
            return self.advisor_names[advisor_idx], self.client_names[client_idx]
        
        return random.choice(self.advisor_names), random.choice(self.client_names)
    
    def sanitize_filename(self, name: str) -> str:
        """Sanitize a name for use in a filename."""
        return name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    
    def save_conversation_file(self, advisor: str, client: str, conversation_file: ConversationFile):
        """Save a conversation file to disk."""
        try:
            # Create advisor directory
            advisor_dir = self.output_dir / self.sanitize_filename(advisor)
            advisor_dir.mkdir(exist_ok=True)
            
            # Create the output file path
            output_file = advisor_dir / f"{client}.json"
            
            # Convert to JSON and save
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(conversation_file.to_dict(), f, indent=2)
            
            print(f"Successfully saved conversation file: {output_file}")
        except Exception as e:
            print(f"Error saving conversation file: {e}")
            raise
    
    async def generate_synthetic_data(self):
        """
        Generate and save synthetic conversations with proper tracking of advisor/client pairs.
        """
        # Generate dummy conversations (in a real scenario, these would come from LLM calls)
        print(f"Starting synthetic data generation with {self.num_conversations} conversations...")
        
        # Create all the conversation generation tasks and track metadata
        for i in range(1, self.num_conversations + 1):
            conversation_type = self.select_conversation_type()
            advisor, client = self.select_advisors_clients()
            num_messages = random.randint(self.min_messages, self.max_messages)
            
            # Get company count from the taxonomy
            company_count = self.get_company_count_for_type(conversation_type)
            
            # Generate a fake topic and subtopic with the proper format
            topic = f"Topic{i}"
            subtopic = f"Subtopic{i}"
            formatted_topic = f"{topic}.{subtopic}"
            
            # Generate dummy messages
            messages = []
            for j in range(num_messages):
                speaker = "0" if j % 2 == 0 else "1"
                text = f"This is message {j+1} of conversation {i} about {formatted_topic}"
                messages.append(Message(speaker, text))
            
            # Generate dummy company mentions
            company_mentions = [f"Company{k}" for k in range(1, company_count + 1)]
            
            # Create conversation object
            conversation_id = f"conv_{i}_{int(time.time())}"
            conversation = SingleConversation(
                conversation_id=conversation_id,
                topic=topic,
                subtopic=subtopic,
                messages=messages,
                company_mentions=company_mentions
            )
            
            # Add to buffer
            buffer_key = f"{advisor}_{client}"
            if buffer_key not in self.conversation_buffer:
                self.conversation_buffer[buffer_key] = ConversationFile(
                    version=self.json_version,
                    advisor=advisor,
                    client=client,
                    conversations=[]
                )
            
            self.conversation_buffer[buffer_key].conversations.append(conversation)
            print(f"Added conversation {conversation_id} to buffer with key {buffer_key}")
        
        # Log each buffer entry and how many conversations it contains
        print(f"Conversation buffer now has {len(self.conversation_buffer)} entries after processing")
        for key, conv_file in self.conversation_buffer.items():
            print(f"Buffer entry '{key}' contains {len(conv_file.conversations)} conversations")
        
        # Save all conversations from the buffer
        for key, conv_file in self.conversation_buffer.items():
            advisor, client = key.split("_", 1) 
            try:
                print(f"Saving {len(conv_file.conversations)} conversations for {advisor} and {client}")
                self.save_conversation_file(advisor, client, conv_file)
                print(f"Successfully saved conversations for {advisor} and {client}")
            except Exception as e:
                print(f"ERROR: Failed to save conversations for {advisor} and {client}: {str(e)}")
                # Try to provide more debug information
                output_path = Path(self.output_dir)
                advisor_dir = output_path / self.sanitize_filename(advisor)
                print(f"Advisor directory path: {advisor_dir}")
                print(f"Directory exists: {advisor_dir.exists()}")
                print(f"Directory writable: {os.access(advisor_dir.parent, os.W_OK)}")

async def main():
    # Initialize the generator
    generator = StandaloneGenerator()
    
    # Run the generation
    await generator.generate_synthetic_data()
    
    # Print summary
    print("\nGeneration completed!")

if __name__ == "__main__":
    asyncio.run(main())
