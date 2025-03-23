#!/usr/bin/env python

"""
Wrapper script for running the synthetic data generation with proper conversation tracking
and avoiding permission issues with the log files.
"""

import asyncio
import json
import os
import sys
import random
import uuid
from datetime import datetime
from pathlib import Path

# Import from the main module
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import SyntheticChatGenerator, ConversationFile, SingleConversation
from config import (
    NUM_CONVERSATIONS, MIN_MESSAGES, MAX_MESSAGES, 
    TAXONOMY_FILE, OUTPUT_DIR, ADVISOR_NAMES, CLIENT_NAMES,
    JSON_VERSION
)

class FixedGenerator(SyntheticChatGenerator):
    """
    Extended generator class that fixes the conversation tracking issue
    """
    
    async def generate_synthetic_data(self):
        """
        Generate and save synthetic conversations with proper tracking of advisor/client pairs.
        """
        tasks = []
        conversation_metadata = []  # Track advisor/client pairs for each conversation
        
        print(f"Starting synthetic data generation with {self.num_conversations} conversations...")
        
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
            
            # Create task
            print(f"Creating task {i} for {advisor} - {client}, type: {conversation_type}")
            tasks.append(self.process_conversation(i, conversation_type, advisor, client, num_messages))
        
        # Wait for all conversation generation to complete
        print(f"Gathering {len(tasks)} conversation generation tasks...")
        conversations = await asyncio.gather(*tasks)
        
        # Filter valid conversations
        valid_conversations = [c for c in conversations if c.conversation_id and not c.conversation_id.endswith("_error")]
        print(f"Generated {len(valid_conversations)} valid conversations out of {len(conversations)} total")
        
        # Check if the buffer already has entries before processing
        print(f"Conversation buffer has {len(self.conversation_buffer)} entries before processing new conversations")
        
        # Add conversations to the buffer using the metadata we tracked
        for i, conversation in enumerate(conversations):
            if conversation.conversation_id and not conversation.conversation_id.endswith("_error"):
                # Get the advisor/client from our metadata
                metadata = conversation_metadata[i]
                advisor = metadata["advisor"]
                client = metadata["client"]
                
                # Create the buffer key
                buffer_key = f"{advisor}_{client}"
                
                # Initialize buffer entry if needed
                if buffer_key not in self.conversation_buffer:
                    self.conversation_buffer[buffer_key] = ConversationFile(
                        version=JSON_VERSION,
                        advisor=advisor,
                        client=client,
                        conversations=[]
                    )
                
                # Add the conversation to the buffer
                self.conversation_buffer[buffer_key].conversations.append(conversation)
                print(f"Added conversation {conversation.conversation_id} to buffer with key {buffer_key}")
        
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
    # Initialize the fixed generator with minimal logging
    generator = FixedGenerator()
    
    # Run the generation
    await generator.generate_synthetic_data()
    
    # Print summary
    print("\nGeneration completed!")

if __name__ == "__main__":
    asyncio.run(main())
