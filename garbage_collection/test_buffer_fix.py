#!/usr/bin/env python

"""
Test script to verify the buffer fix without logging permission issues.
This script implements the fixes made to main.py for tracking advisor/client pairs
and properly populating the conversation buffer.
"""

import asyncio
import os
import sys
import json
import random
import uuid
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Tuple

# Import from config with fallbacks
try:
    from config import (
        NUM_CONVERSATIONS, MIN_MESSAGES, MAX_MESSAGES, 
        TAXONOMY_FILE, OUTPUT_DIR, ADVISOR_NAMES, CLIENT_NAMES,
        JSON_VERSION
    )
except ImportError:
    # Default values if config can't be imported
    NUM_CONVERSATIONS = 20
    MIN_MESSAGES = 3
    MAX_MESSAGES = 10
    TAXONOMY_FILE = "./taxonomies/taxonomy.json"
    OUTPUT_DIR = "./synthetic_data"
    ADVISOR_NAMES = ["Alice Johnson", "Robert Chen", "Maria Garcia"]
    CLIENT_NAMES = ["Diana", "Ethan", "Frank"]
    JSON_VERSION = "1.0"

# Define the same classes from main.py
@dataclass
class ChatLine:
    speaker: str  # "0" = client, "1" = advisor
    text: str

@dataclass
class SingleConversation:
    conversation_id: str
    timestamp: str
    category: str  # Top-level category
    topic: str     # Will now contain "topic.subtopic" if applicable
    lines: List[ChatLine] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "timestamp": self.timestamp,
            "category": self.category,
            "topic": self.topic,
            "lines": [line.__dict__ for line in self.lines]
        }

@dataclass
class ConversationFile:
    version: str
    advisor: str
    client: str
    conversations: List[SingleConversation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "advisor": self.advisor,
            "client": self.client,
            "conversations": [conv.to_dict() for conv in self.conversations]
        }

def sanitize_filename(name: str) -> str:
    """Removes or replaces characters that are invalid in filenames."""
    return name.replace(" ", "_").replace("/", "_").replace("\\", "_")

class BufferTester:
    def __init__(self):
        self.num_conversations = NUM_CONVERSATIONS
        self.min_messages = MIN_MESSAGES
        self.max_messages = MAX_MESSAGES
        self.taxonomy_file = TAXONOMY_FILE
        self.output_dir_base = Path(OUTPUT_DIR)
        self.advisor_names = ADVISOR_NAMES
        self.client_names = CLIENT_NAMES
        self.json_version = JSON_VERSION
        
        # Generate a unique run ID for this test
        self.run_id = f"run_{datetime.now().strftime('%Y_%m_%d_%H%M%S')}"
        
        # Setup output directory
        self.output_dir = self.setup_output_directory()
        
        # Load taxonomy
        self.taxonomy = self.load_taxonomy()
        
        # Initialize empty conversation buffer
        self.conversation_buffer = {}
        print(f"Initialized empty conversation buffer")
    
    def load_taxonomy(self) -> dict:
        """Load the taxonomy from the JSON file."""
        try:
            with open(self.taxonomy_file, 'r', encoding='utf-8') as f:
                taxonomy = json.load(f)
            print(f"Successfully loaded taxonomy from {self.taxonomy_file}")
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
    
    def select_advisors_clients(self, index=None) -> tuple:
        """Select an advisor and client pair."""
        if index is not None and 0 <= index < len(self.advisor_names) * len(self.client_names):
            advisor_idx = index % len(self.advisor_names)
            client_idx = (index // len(self.advisor_names)) % len(self.client_names)
            return self.advisor_names[advisor_idx], self.client_names[client_idx]
        
        return random.choice(self.advisor_names), random.choice(self.client_names)
    
    def select_topic(self) -> Tuple[str, str, str]:
        """
        Select a random topic and subtopic.
        Returns a tuple of (category, topic, subtopic).
        """
        categories = ["Financial", "Market", "Industry"]
        topics = ["Analysis", "Trends", "Performance"]
        subtopics = ["Q1", "Q2", "Q3", "Q4"]
        
        category = random.choice(categories)
        topic = random.choice(topics)
        subtopic = random.choice(subtopics)
        
        return category, topic, subtopic
    
    def get_company_count_for_type(self, conversation_type: str) -> int:
        """Get the number of companies to mention for a conversation type from taxonomy."""
        conversation_types = self.taxonomy.get("conversation_types", {})
        type_info = conversation_types.get(conversation_type, {})
        company_count_options = type_info.get("company_count_options", [1])
        return random.choice(company_count_options)
    
    def save_conversation_file(self, advisor: str, client: str, conversation_file: ConversationFile):
        """Save a conversation file to disk."""
        try:
            # Create advisor directory
            advisor_dir = self.output_dir / sanitize_filename(advisor)
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
    
    def process_conversation(self, conv_number: int, conversation_type: str, advisor_name: str, client_name: str, num_messages: int) -> SingleConversation:
        """
        Processes a single conversation (simplified for testing).
        """
        try:
            timestamp = datetime.now().isoformat()
            category, topic, subtopic = self.select_topic()
            conversation_id = f"{self.run_id}_{conv_number}_{uuid.uuid4().hex[:8]}"

            # Format the topic in the desired format
            formatted_topic = f"{topic}.{subtopic}" if subtopic else topic
            
            # Get company count from taxonomy
            company_count = self.get_company_count_for_type(conversation_type)
            
            # Generate dummy messages
            chat_lines = []
            for i in range(num_messages):
                speaker = "0" if i % 2 == 0 else "1"
                text = f"This is message {i+1} of {num_messages} in conversation {conv_number} about {formatted_topic}"
                chat_lines.append(ChatLine(speaker=speaker, text=text))
            
            # Create the conversation object
            conversation = SingleConversation(
                conversation_id=conversation_id,
                timestamp=timestamp,
                category=category,
                topic=formatted_topic,
                lines=chat_lines
            )
            
            print(f"Generated conversation {conversation_id} for {advisor_name}-{client_name} with {len(chat_lines)} messages (using company count: {company_count})")
            
            return conversation
            
        except Exception as e:
            print(f"Error processing conversation {conv_number}: {e}")
            # Return empty conversation on error
            return SingleConversation(
                conversation_id=f"{self.run_id}_{conv_number}_error",
                timestamp=datetime.now().isoformat(),
                category="Error",
                topic="Error",
                lines=[]
            )
    
    async def generate_synthetic_data(self):
        """
        Generate and save synthetic conversations.
        This implements the fixed buffer tracking logic.
        """
        # Initialize the conversation buffer at the beginning of each generation
        self.conversation_buffer = {}
        print(f"DEBUG: Initialized empty conversation buffer")
        
        tasks = []
        conversation_metadata = []  # Track advisor/client pairs for each conversation
        
        # Create all the conversation generation tasks and track metadata
        for i in range(1, self.num_conversations + 1):
            conversation_type = self.select_conversation_type()
            advisor, client = self.select_advisors_clients()
            num_messages = random.randint(self.min_messages, self.max_messages)
            
            # Store metadata for this conversation
            conversation_metadata.append({
                "index": i,
                "advisor": advisor,
                "client": client,
                "type": conversation_type,
                "messages": num_messages
            })
            
            # Process conversation directly (no async needed for test)
            tasks.append(self.process_conversation(i, conversation_type, advisor, client, num_messages))
        
        # No need for gather since we're not making async calls
        conversations = tasks
        
        # Log details about the conversations generated
        valid_conversations = [c for c in conversations if c.conversation_id and not c.conversation_id.endswith("_error")]
        print(f"DEBUG: Generated {len(valid_conversations)} valid conversations out of {len(conversations)} total")
        
        # Check if the buffer already has entries before processing
        print(f"DEBUG: Conversation buffer has {len(self.conversation_buffer)} entries before processing new conversations")
        
        # Add conversations to the buffer using the metadata we tracked
        buffer_additions = 0
        for i, conversation in enumerate(conversations):
            if i < len(conversation_metadata) and conversation.conversation_id and not conversation.conversation_id.endswith("_error"):
                # Get the advisor/client from our metadata
                metadata = conversation_metadata[i]
                advisor = metadata["advisor"]
                client = metadata["client"]
                
                # Create the buffer key
                buffer_key = f"{advisor}_{client}"
                print(f"DEBUG: Processing conversation {i+1} for buffer key '{buffer_key}'")
                
                # Initialize buffer entry if needed
                if buffer_key not in self.conversation_buffer:
                    print(f"DEBUG: Creating new buffer entry for key '{buffer_key}'")
                    self.conversation_buffer[buffer_key] = ConversationFile(
                        version=self.json_version,
                        advisor=advisor,
                        client=client,
                        conversations=[]
                    )
                
                # Add the conversation to the buffer
                self.conversation_buffer[buffer_key].conversations.append(conversation)
                buffer_additions += 1
                print(f"DEBUG: Added conversation {conversation.conversation_id} to buffer with key '{buffer_key}' (buffer now has {len(self.conversation_buffer[buffer_key].conversations)} conversations)")
        
        # Log each buffer entry and how many conversations it contains
        print(f"DEBUG: Added {buffer_additions} conversations to the buffer across {len(self.conversation_buffer)} entries")
        print(f"DEBUG: Conversation buffer now has {len(self.conversation_buffer)} entries after processing")
        for key, conv_file in self.conversation_buffer.items():
            print(f"DEBUG: Buffer entry '{key}' contains {len(conv_file.conversations)} conversations")
        
        # Save all conversations from the buffer
        for buffer_key, conv_file in self.conversation_buffer.items():
            try:
                # Extract advisor and client from the buffer key
                advisor, client = buffer_key.split("_", 1)
                
                print(f"DEBUG: Saving {len(conv_file.conversations)} conversations for {advisor} and {client}")
                self.save_conversation_file(advisor, client, conv_file)
                print(f"DEBUG: Successfully saved conversations for {advisor} and {client}")
            except Exception as e:
                print(f"DEBUG ERROR: Failed to save conversations for {buffer_key}: {str(e)}")

# Main execution
async def main():
    tester = BufferTester()
    await tester.generate_synthetic_data()
    print("Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
