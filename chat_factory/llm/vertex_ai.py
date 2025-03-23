"""
Vertex AI implementation of LLM provider (using GenAI SDK for Gemini 2.0 support).
"""

import logging
import random
import asyncio
import os
from typing import Optional, Union

# Direct imports to avoid try/except issues
# We'll handle import errors in the class initialization
USING_GENAI_SDK = False
genai = None
vertexai = None
GenerativeModel = None
GenerationConfig = None
HttpOptions = None

try:
    from google import genai
    from google.genai.types import HttpOptions
    USING_GENAI_SDK = True
    logging.info("Successfully imported GenAI SDK")
except ImportError:
    logging.warning("Google GenAI SDK (google-genai) not available")

try:
    import vertexai
    from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
    logging.info("Successfully imported Vertex AI SDK")
except ImportError:
    logging.warning("Vertex AI SDK (vertexai) not available")

# Check if either SDK is available
if not USING_GENAI_SDK and vertexai is None:
    logging.error("Neither GenAI SDK nor Vertex AI SDK are available")

from .base import LLMProvider


class VertexAIProvider(LLMProvider):
    """
    LLM provider implementation for Google Cloud Vertex AI.
    Supports both Gemini 1.5 (via Vertex AI SDK) and Gemini 2.0 (via GenAI SDK).
    """
    
    def __init__(self, config):
        """
        Initialize the Vertex AI provider with configuration.
        
        Args:
            config: Configuration object with Vertex AI settings
        """
        super().__init__(config)
        self.project_id = getattr(config, 'PROJECT_ID', '')
        self.location = getattr(config, 'LOCATION', 'us-central1')
        self.model_name = getattr(config, 'MODEL_NAME', 'gemini-1.5-flash-002').lower()
        self.temperature = getattr(config, 'TEMPERATURE', 0.3)
        self.top_p = getattr(config, 'TOP_P', 1.0)
        self.top_k = getattr(config, 'TOP_K', 40)
        self.api_version = getattr(config, 'API_VERSION', 'v1')
        self.use_genai_sdk = getattr(config, 'USE_GENAI_SDK', None)
        self.presence_penalty = getattr(config, 'PRESENCE_PENALTY', 0.0)
        self.frequency_penalty = getattr(config, 'FREQUENCY_PENALTY', 0.0)
        self.stop_sequences = getattr(config, 'STOP_SEQUENCES', [])
        
        
        # Determine which SDK to use based on the model name and config
        if self.use_genai_sdk is None:
            # Auto-detect based on model name and available SDKs
            self.use_genai_sdk = USING_GENAI_SDK and self.model_name.startswith("gemini-2")
        else:
            if self.use_genai_sdk and not USING_GENAI_SDK:
                logging.warning("GenAI SDK requested but not installed. Falling back to Vertex AI SDK.")
                self.use_genai_sdk = False
        
        # Validate SDK availability
        if self.use_genai_sdk and genai is None:
            raise ImportError("Google GenAI SDK requested but not available. Install with 'pip install google-genai'")
        elif not self.use_genai_sdk and vertexai is None:
            raise ImportError("Vertex AI SDK requested but not available. Install with 'pip install vertexai google-cloud-aiplatform'")
        
        self.llm = None
        self.genai_client = None
    
    async def initialize(self):
        """
        Initialize the appropriate client and model based on the SDK choice.
        """
        logging.info(f"Initializing Vertex AI with project {self.project_id} in {self.location}")
        
        try:
            if self.use_genai_sdk:
                await self._initialize_genai()
            else:
                await self._initialize_vertexai()
        except Exception as e:
            logging.error(f"Error initializing AI service: {e}", exc_info=True)
            raise
    
    async def _initialize_genai(self):
        """Initialize using the GenAI SDK for Gemini 2.0."""
        if genai is None:
            raise ImportError("Google GenAI SDK not available but required for this mode")
            
        # Set environment variables for GenAI with Vertex AI
        os.environ["GOOGLE_CLOUD_PROJECT"] = self.project_id
        os.environ["GOOGLE_CLOUD_LOCATION"] = self.location
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
        
        # Initialize the client
        self.genai_client = genai.Client(http_options=HttpOptions(api_version=self.api_version))
        logging.info(f"Successfully initialized GenAI client with API version: {self.api_version}")
        
        #Test model availability
        try:
            models = self.genai_client.list()
            model_found = False
            
            for model in models:
                if self.model_name in model.name:
                    model_found = True
                    break
            
            if not model_found:
                logging.warning(f"Model {self.model_name} not found in available models. Using the model anyway.")
        except Exception as e:
            logging.warning(f"Could not check model availability: {e}")
    
    async def _initialize_vertexai(self):
        """Initialize using the Vertex AI SDK for Gemini 1.5 and earlier."""
        if vertexai is None:
            raise ImportError("Vertex AI SDK not available but required for this mode")
            
        vertexai.init(project=self.project_id, location=self.location)
        self.llm = GenerativeModel(self.model_name)
        logging.info(f"Successfully initialized Vertex AI model: {self.model_name}")
    
    async def generate_content(self, prompt: str, max_tokens: Optional[int] = None) -> str:
        """
        Generate content using the appropriate SDK.
        
        Args:
            prompt: The prompt to send to the LLM
            max_tokens: Maximum number of tokens to generate (optional)
            
        Returns:
            Generated content as a string
        """
        if self.use_genai_sdk and self.genai_client is None:
            await self._initialize_genai()
        elif not self.use_genai_sdk and self.llm is None:
            await self._initialize_vertexai()
        
        try:
            if self.use_genai_sdk:
                generation_config = {
                    "max_output_tokens": max_tokens or 1200,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "top_k": self.top_k,
                    "presence_penalty": self.presence_penalty,
                    "frequency_penalty": self.frequency_penalty
                    #"stop_sequences": self.stop_sequences     
                }
                
                response = self.genai_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=generation_config
                )
                
                return response.text.strip()
            else:
                generation_config = GenerationConfig(
                    max_output_tokens=max_tokens or 1200,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    top_k=self.top_k
                )
                
                response = await self.llm.generate_content_async(
                    contents=[prompt],
                    generation_config=generation_config,
                    stream=False
                )
                
                return response.candidates[0].content.text.strip()
        except Exception as e:
            logging.error(f"Error generating content: {e}", exc_info=True)
            return ""
    
    async def retry_with_backoff(self, prompt: str, max_retries: int = 10, 
                          initial_backoff: float = 1.0, max_backoff: float = 32.0) -> str:
        """
        Call AI service with exponential backoff retry logic for handling rate limits.
        
        Args:
            prompt: The prompt to send to the LLM
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff time in seconds
            max_backoff: Maximum backoff time in seconds
            
        Returns:
            Generated content as a string
        """
        if self.use_genai_sdk and self.genai_client is None:
            await self._initialize_genai()
        elif not self.use_genai_sdk and self.llm is None:
            await self._initialize_vertexai()
        
        backoff = initial_backoff
        attempt = 0
        
        while attempt <= max_retries:
            try:
                attempt += 1
                
                if attempt > 1:
                    logging.info(f"API call attempt {attempt}/{max_retries+1}")
                
                if self.use_genai_sdk:
                    generation_config = {
                        "max_output_tokens": 1200,
                        "temperature": self.temperature,
                        "top_p": self.top_p,
                        "top_k": self.top_k,
                        "presence_penalty": self.presence_penalty,
                        "frequency_penalty": self.frequency_penalty
                        #"stop_sequences": self.stop_sequences
                    }
                    
                    # Note: The new client doesn't have an async method, so we'll run it in the default thread pool
                    response = await asyncio.to_thread(
                        self.genai_client.models.generate_content,
                        model=self.model_name,
                        contents=prompt,
                        config=generation_config
                    )
                    
                    raw_response = response.text.strip()
                else:
                    generation_config = GenerationConfig(
                        max_output_tokens=1200,
                        temperature=self.temperature,
                        top_p=self.top_p,
                        top_k=self.top_k
                    )
                    
                    response = await self.llm.generate_content_async(
                        contents=[prompt],
                        generation_config=generation_config,
                        stream=False
                    )
                    
                    raw_response = response.candidates[0].content.text.strip()
                
                logging.debug(f"Raw LLM Response: {raw_response[:100]}...")
                return raw_response
                
            except Exception as e:
                error_message = str(e)
                
                # Check if this is a rate limit error (429)
                if "429" in error_message or "quota" in error_message.lower() or "rate limit" in error_message.lower():
                    if attempt <= max_retries:
                        # Calculate backoff with jitter (up to 25% randomness)
                        jitter = random.uniform(0, 0.25 * backoff)
                        sleep_time = backoff + jitter
                        
                        logging.warning(f"Rate limit (429) hit. Retrying in {sleep_time:.2f} seconds (attempt {attempt}/{max_retries+1})")
                        await asyncio.sleep(sleep_time)
                        
                        # Exponential backoff with truncation
                        backoff = min(backoff * 2, max_backoff)
                    else:
                        logging.error(f"Maximum retry attempts ({max_retries+1}) reached for rate limit errors.")
                        return ""
                else:
                    # For non-rate-limit errors, log and return immediately
                    logging.error(f"Error calling AI service: {e}", exc_info=True)
                    return ""
        
        # This point is reached if we've exhausted all retries
        logging.error(f"Failed to get a response after {max_retries+1} attempts")
        return ""