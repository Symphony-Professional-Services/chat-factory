# """
# Vertex AI implementation of LLM provider (using GenAI SDK for Gemini 2.0 support).
# """

# import logging
# import random
# import asyncio
# import os
# from typing import Optional, Union

# # Direct imports to avoid try/except issues
# # We'll handle import errors in the class initialization
# USING_GENAI_SDK = False
# genai = None
# vertexai = None
# GenerativeModel = None
# GenerationConfig = None
# HttpOptions = None

# try:
#     from google import genai
#     from google.genai.types import HttpOptions
#     USING_GENAI_SDK = True
#     logging.info("Successfully imported GenAI SDK")
# except ImportError:
#     logging.warning("Google GenAI SDK (google-genai) not available")

# try:
#     import vertexai
#     from vertexai.preview.generative_models import GenerativeModel, GenerationConfig
#     logging.info("Successfully imported Vertex AI SDK")
# except ImportError:
#     logging.warning("Vertex AI SDK (vertexai) not available")

# # Check if either SDK is available
# if not USING_GENAI_SDK and vertexai is None:
#     logging.error("Neither GenAI SDK nor Vertex AI SDK are available")

# from .base import LLMProvider


# class VertexAIProvider(LLMProvider):
#     """
#     LLM provider implementation for Google Cloud Vertex AI.
#     Supports both Gemini 1.5 (via Vertex AI SDK) and Gemini 2.0 (via GenAI SDK).
#     """
    
#     def __init__(self, config):
#         """
#         Initialize the Vertex AI provider with configuration.
        
#         Args:
#             config: Configuration object with Vertex AI settings
#         """
#         super().__init__(config)
#         self.project_id = getattr(config, 'PROJECT_ID', '')
#         self.location = getattr(config, 'LOCATION', 'us-central1')
#         self.model_name = getattr(config, 'MODEL_NAME', 'gemini-1.5-flash-002').lower()
#         self.temperature = getattr(config, 'TEMPERATURE', 0.3)
#         self.top_p = getattr(config, 'TOP_P', 1.0)
#         self.top_k = getattr(config, 'TOP_K', 40)
#         self.api_version = getattr(config, 'API_VERSION', 'v1')
#         self.use_genai_sdk = getattr(config, 'USE_GENAI_SDK', None)
#         self.presence_penalty = getattr(config, 'PRESENCE_PENALTY', 0.0)
#         self.frequency_penalty = getattr(config, 'FREQUENCY_PENALTY', 0.0)
#         self.stop_sequences = getattr(config, 'STOP_SEQUENCES', [])
        
        
#         # Determine which SDK to use based on the model name and config
#         if self.use_genai_sdk is None:
#             # Auto-detect based on model name and available SDKs
#             self.use_genai_sdk = USING_GENAI_SDK and self.model_name.startswith("gemini-2")
#         else:
#             if self.use_genai_sdk and not USING_GENAI_SDK:
#                 logging.warning("GenAI SDK requested but not installed. Falling back to Vertex AI SDK.")
#                 self.use_genai_sdk = False
        
#         # Validate SDK availability
#         if self.use_genai_sdk and genai is None:
#             raise ImportError("Google GenAI SDK requested but not available. Install with 'pip install google-genai'")
#         elif not self.use_genai_sdk and vertexai is None:
#             raise ImportError("Vertex AI SDK requested but not available. Install with 'pip install vertexai google-cloud-aiplatform'")
        
#         self.llm = None
#         self.genai_client = None
    
#     async def initialize(self):
#         """
#         Initialize the appropriate client and model based on the SDK choice.
#         """
#         logging.info(f"Initializing Vertex AI with project {self.project_id} in {self.location}")
        
#         try:
#             if self.use_genai_sdk:
#                 await self._initialize_genai()
#             else:
#                 await self._initialize_vertexai()
#         except Exception as e:
#             logging.error(f"Error initializing AI service: {e}", exc_info=True)
#             raise
    
#     async def _initialize_genai(self):
#         """Initialize using the GenAI SDK for Gemini 2.0."""
#         if genai is None:
#             raise ImportError("Google GenAI SDK not available but required for this mode")
            
#         # Set environment variables for GenAI with Vertex AI
#         os.environ["GOOGLE_CLOUD_PROJECT"] = self.project_id
#         os.environ["GOOGLE_CLOUD_LOCATION"] = self.location
#         os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
        
#         # Initialize the client
#         self.genai_client = genai.Client(http_options=HttpOptions(api_version=self.api_version))
#         logging.info(f"Successfully initialized GenAI client with API version: {self.api_version}")
        
#         #Test model availability
#         try:
#             models = self.genai_client.list()
#             model_found = False
            
#             for model in models:
#                 if self.model_name in model.name:
#                     model_found = True
#                     break
            
#             if not model_found:
#                 logging.warning(f"Model {self.model_name} not found in available models. Using the model anyway.")
#         except Exception as e:
#             logging.warning(f"Could not check model availability: {e}")
    
#     async def _initialize_vertexai(self):
#         """Initialize using the Vertex AI SDK for Gemini 1.5 and earlier."""
#         if vertexai is None:
#             raise ImportError("Vertex AI SDK not available but required for this mode")
            
#         vertexai.init(project=self.project_id, location=self.location)
#         self.llm = GenerativeModel(self.model_name)
#         logging.info(f"Successfully initialized Vertex AI model: {self.model_name}")
    
#     async def generate_content(self, prompt: str, max_tokens: Optional[int] = None) -> str:
#         """
#         Generate content using the appropriate SDK.
        
#         Args:
#             prompt: The prompt to send to the LLM
#             max_tokens: Maximum number of tokens to generate (optional)
            
#         Returns:
#             Generated content as a string
#         """
#         if self.use_genai_sdk and self.genai_client is None:
#             await self._initialize_genai()
#         elif not self.use_genai_sdk and self.llm is None:
#             await self._initialize_vertexai()
        
#         try:
#             if self.use_genai_sdk:
#                 generation_config = {
#                     "max_output_tokens": max_tokens or 1200,
#                     "temperature": self.temperature,
#                     "top_p": self.top_p,
#                     "top_k": self.top_k,
#                     "presence_penalty": self.presence_penalty,
#                     "frequency_penalty": self.frequency_penalty
#                     #"stop_sequences": self.stop_sequences     
#                 }
                
#                 response = self.genai_client.models.generate_content(
#                     model=self.model_name,
#                     contents=prompt,
#                     config=generation_config
#                 )
                
#                 return response.text.strip()
#             else:
#                 generation_config = GenerationConfig(
#                     max_output_tokens=max_tokens or 1200,
#                     temperature=self.temperature,
#                     top_p=self.top_p,
#                     top_k=self.top_k
#                 )
                
#                 response = await self.llm.generate_content_async(
#                     contents=[prompt],
#                     generation_config=generation_config,
#                     stream=False
#                 )
                
#                 return response.candidates[0].content.text.strip()
#         except Exception as e:
#             logging.error(f"Error generating content: {e}", exc_info=True)
#             return ""
    
#     async def retry_with_backoff(self, prompt: str, max_retries: int = 10, 
#                           initial_backoff: float = 1.0, max_backoff: float = 32.0) -> str:
#         """
#         Call AI service with exponential backoff retry logic for handling rate limits.
        
#         Args:
#             prompt: The prompt to send to the LLM
#             max_retries: Maximum number of retry attempts
#             initial_backoff: Initial backoff time in seconds
#             max_backoff: Maximum backoff time in seconds
            
#         Returns:
#             Generated content as a string
#         """
#         if self.use_genai_sdk and self.genai_client is None:
#             await self._initialize_genai()
#         elif not self.use_genai_sdk and self.llm is None:
#             await self._initialize_vertexai()
        
#         backoff = initial_backoff
#         attempt = 0
        
#         while attempt <= max_retries:
#             try:
#                 attempt += 1
                
#                 if attempt > 1:
#                     logging.info(f"API call attempt {attempt}/{max_retries+1}")
                
#                 if self.use_genai_sdk:
#                     generation_config = {
#                         "max_output_tokens": 1200,
#                         "temperature": self.temperature,
#                         "top_p": self.top_p,
#                         "top_k": self.top_k,
#                         "presence_penalty": self.presence_penalty,
#                         "frequency_penalty": self.frequency_penalty
#                         #"stop_sequences": self.stop_sequences
#                     }
                    
#                     # Note: The new client doesn't have an async method, so we'll run it in the default thread pool
#                     response = await asyncio.to_thread(
#                         self.genai_client.models.generate_content,
#                         model=self.model_name,
#                         contents=prompt,
#                         config=generation_config
#                     )
                    
#                     raw_response = response.text.strip()
#                 else:
#                     generation_config = GenerationConfig(
#                         max_output_tokens=1200,
#                         temperature=self.temperature,
#                         top_p=self.top_p,
#                         top_k=self.top_k
#                     )
                    
#                     response = await self.llm.generate_content_async(
#                         contents=[prompt],
#                         generation_config=generation_config,
#                         stream=False
#                     )
                    
#                     raw_response = response.candidates[0].content.text.strip()
                
#                 logging.debug(f"Raw LLM Response: {raw_response[:100]}...")
#                 return raw_response
                
#             except Exception as e:
#                 error_message = str(e)
                
#                 # Check if this is a rate limit error (429)
#                 if "429" in error_message or "quota" in error_message.lower() or "rate limit" in error_message.lower():
#                     if attempt <= max_retries:
#                         # Calculate backoff with jitter (up to 25% randomness)
#                         jitter = random.uniform(0, 0.25 * backoff)
#                         sleep_time = backoff + jitter
                        
#                         logging.warning(f"Rate limit (429) hit. Retrying in {sleep_time:.2f} seconds (attempt {attempt}/{max_retries+1})")
#                         await asyncio.sleep(sleep_time)
                        
#                         # Exponential backoff with truncation
#                         backoff = min(backoff * 2, max_backoff)
#                     else:
#                         logging.error(f"Maximum retry attempts ({max_retries+1}) reached for rate limit errors.")
#                         return ""
#                 else:
#                     # For non-rate-limit errors, log and return immediately
#                     logging.error(f"Error calling AI service: {e}", exc_info=True)
#                     return ""
        
#         # This point is reached if we've exhausted all retries
#         logging.error(f"Failed to get a response after {max_retries+1} attempts")
#         return ""


"""
Vertex AI implementation of LLM provider (using GenAI SDK for Gemini 2.0 support).
"""

import logging
import random
import asyncio
import os
import time  # Added for timing
from typing import Optional, Union, List, Dict # Added List, Dict

# Direct imports to avoid try/except issues
# We'll handle import errors in the class initialization
USING_GENAI_SDK = False
genai = None
vertexai = None
GenerativeModel = None
GenerationConfig = None
HttpOptions = None
Part = None # For Vertex AI SDK response structure

# Get a logger instance for this module
logger = logging.getLogger(__name__)

# try:
#     # Use configure for API key if needed, but rely on env vars/ADC by default
#     from google import genai
#     from google.genai.types import HttpOptions
#     USING_GENAI_SDK = True
#     logger.info("Successfully imported GenAI SDK (google-genai)")
# except ImportError:
#     logger.warning("Google GenAI SDK (google-genai) not available")

try:
    from google import genai
    from google.genai import types as genai_types # Import the types module
    from google.genai.types import HttpOptions
    USING_GENAI_SDK = True
    logger.info("Successfully imported GenAI SDK (google-genai)")
except ImportError:
    logger.warning("Google GenAI SDK (google-genai) not available")
    genai_types = None # Define as None if import fails
try:
    import vertexai
    # Updated import path based on common usage
    from vertexai.generative_models import GenerativeModel, GenerationConfig
    from google.genai.types import GenerateContentConfig, Part, SafetySetting

    logger.info("Successfully imported Vertex AI SDK (google-cloud-aiplatform)")
except ImportError:
    logger.warning("Vertex AI SDK (google-cloud-aiplatform) not available")

# Check if either SDK is available
if not USING_GENAI_SDK and vertexai is None:
    logger.error("Neither GenAI SDK nor Vertex AI SDK are available")
    # Consider raising an error here if neither is installed, as the provider is unusable

from .base import LLMProvider


class VertexAIProvider(LLMProvider):
    """
    LLM provider implementation for Google Cloud Vertex AI.
    Supports both Gemini 1.5 (via Vertex AI SDK) and Gemini 2.0 / 1.5 Flash (via GenAI SDK).
    Uses native async calls where available.
    """

    def __init__(self, config):
        """
        Initialize the Vertex AI provider with configuration.

        Args:
            config: Configuration object with Vertex AI settings
        """
        super().__init__(config)
        self.project_id = getattr(config, 'PROJECT_ID', os.environ.get('GOOGLE_CLOUD_PROJECT', '')) # Get from env if not in config
        self.location = getattr(config, 'LOCATION', os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')) # Get from env
        # Ensure model_name doesn't have 'models/' prefix initially for logic
        _model_name_config = getattr(config, 'MODEL_NAME', 'gemini-1.5-flash-latest') # Use 'latest' as default?
        self.model_name = _model_name_config.split('/')[-1].lower() # Store base name

        self.temperature = getattr(config, 'TEMPERATURE', 0.3)
        self.top_p = getattr(config, 'TOP_P', 1.0)
        self.top_k = getattr(config, 'TOP_K', 40)
        # API Version likely not needed for google-genai when using Vertex backend
        # self.api_version = getattr(config, 'API_VERSION', 'v1beta') # v1beta common for genai
        self.use_genai_sdk = getattr(config, 'USE_GENAI_SDK', None)
        self.presence_penalty = getattr(config, 'PRESENCE_PENALTY', 0.0) # Note: Not standard in Gemini API? Verify usage.
        self.frequency_penalty = getattr(config, 'FREQUENCY_PENALTY', 0.0) # Note: Not standard in Gemini API? Verify usage.
        self.stop_sequences = getattr(config, 'STOP_SEQUENCES', [])

        # Determine which SDK to use based on available SDKs and config preference
        if self.use_genai_sdk is None:
            # Default to GenAI SDK if available, otherwise use Vertex AI SDK if available
            self.use_genai_sdk = USING_GENAI_SDK
            if not USING_GENAI_SDK and vertexai is None:
                 raise RuntimeError("Configuration requires Vertex/Gemini, but neither google-genai nor google-cloud-aiplatform SDK is installed.")
            elif not USING_GENAI_SDK:
                 logger.info("google-genai SDK not found, defaulting to google-cloud-aiplatform SDK.")
            else:
                 logger.info("Defaulting to use google-genai SDK.")
        elif self.use_genai_sdk and not USING_GENAI_SDK:
            if vertexai is None:
                 raise ImportError("Google GenAI SDK requested but not available, and Vertex AI SDK fallback is also not available.")
            logger.warning("Google GenAI SDK requested but not installed. Falling back to Vertex AI SDK.")
            self.use_genai_sdk = False
        elif not self.use_genai_sdk and vertexai is None:
             if USING_GENAI_SDK:
                  logger.warning("Vertex AI SDK requested but not installed. Falling back to GenAI SDK.")
                  self.use_genai_sdk = True
             else:
                  raise ImportError("Vertex AI SDK requested but not available, and GenAI SDK fallback is also not available.")


        self.llm = None
        self.genai_client = None

    async def initialize(self):
        """
        Initialize the appropriate client and model based on the SDK choice.
        """
        logger.info(f"Initializing Vertex AI provider (using {'GenAI SDK' if self.use_genai_sdk else 'Vertex AI SDK'}) with project='{self.project_id}', location='{self.location}'")

        try:
            if self.use_genai_sdk:
                await self._initialize_genai()
            else:
                await self._initialize_vertexai()
        except Exception as e:
            logger.error(f"Error initializing AI service: {e}", exc_info=True)
            raise

    async def _initialize_genai(self):
        """Initialize using the GenAI SDK configured for Vertex AI backend."""
        if genai is None:
            # This check should be redundant due to __init__ validation, but keep for safety
            raise ImportError("Google GenAI SDK not available but required for this mode")

        # Ensure credentials are configured - usually handled by Application Default Credentials (ADC)
        # You might explicitly configure here if needed:
        # genai.configure(api_key="YOUR_API_KEY") # Or use ADC

        # *** Set environment variables for GenAI to use Vertex AI backend ***
        # This might not be needed if using ADC correctly, but included per original code
        # Best practice is usually ADC without setting these explicitly if possible
        if self.project_id:
            os.environ["GOOGLE_CLOUD_PROJECT"] = self.project_id
        if self.location:
            os.environ["GOOGLE_CLOUD_LOCATION"] = self.location
        # Tell the genai SDK to route requests through Vertex AI
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"

        # Initialize the client - HttpOptions are typically optional when using Vertex backend
        # self.genai_client = genai.Client(http_options=HttpOptions(api_version=self.api_version))
        self.genai_client = genai.Client() # Simpler init often works
        logger.info("Successfully initialized GenAI client (configured for Vertex AI backend).")

        # Test model availability (optional, synchronous, might block if network is slow)
        # Consider making this async if 'genai.aiao.models.list()' or similar exists and is needed
        try:
            logger.debug(f"Checking availability for model containing '{self.model_name}'...")
            # NOTE: genai.list_models() is synchronous
            models = genai.list_models() # Use the top-level function
            model_found = False
            found_model_name = "N/A"

            for model in models:
                # Check if the base model name is in the listed model's name (which might be models/...)
                if self.model_name in model.name:
                    model_found = True
                    found_model_name = model.name
                    break

            if model_found:
                 logger.info(f"Model check: Found matching model '{found_model_name}' via genai.list_models().")
            else:
                logger.warning(f"Model check: Model containing '{self.model_name}' not found in available models via genai.list_models(). Will attempt to use 'models/{self.model_name}' anyway.")
        except Exception as e:
            logger.warning(f"Could not check model availability via genai.list_models(): {e}")


    async def _initialize_vertexai(self):
        """Initialize using the Vertex AI SDK."""
        if vertexai is None:
             # Redundant check, but safe
            raise ImportError("Vertex AI SDK not available but required for this mode")

        # Initialize Vertex AI SDK - usually finds ADC automatically
        vertexai.init(project=self.project_id, location=self.location)
        self.llm = GenerativeModel(self.model_name) # Use base model name
        logger.info(f"Successfully initialized Vertex AI SDK model: {self.model_name}")

    # generate_content method is likely redundant if only retry_with_backoff is called externally.
    # Keep it for now, but ensure logic matches the single attempt inside retry_with_backoff
    # async def generate_content(self, prompt: str, max_tokens: Optional[int] = None) -> str:
    #    # ... Logic to call the correct SDK once ...
    #    pass

    async def generate_content(self, prompt: str, max_tokens: Optional[int] = None) -> Optional[str]:
        """
        Generate content using the configured LLM provider (single attempt).
        This method implements the abstract method required by LLMProvider.
        It delegates to retry_with_backoff with 0 retries for the actual call.

        Args:
            prompt: The prompt to send to the LLM.
            max_tokens: Maximum number of tokens (Note: Currently not passed directly
                        to the underlying call which uses class config attributes.
                        Modify retry_with_backoff if override is needed).

        Returns:
            Generated content as a string, or None on failure.
        """
        logger.debug(f"generate_content called (delegating to retry_with_backoff with max_retries=0)")
        # We call retry_with_backoff with max_retries=0 to perform a single attempt
        # using the consolidated logic already present there.
        # The max_tokens parameter isn't directly used here because the generation config
        # in retry_with_backoff pulls from self.config. If needed, retry_with_backoff
        # could be modified to accept and prioritize a max_tokens argument.
        return await self.retry_with_backoff(prompt=prompt, max_retries=0)


    async def retry_with_backoff(self, prompt: str,
                                    max_retries: int = 5,
                                    initial_backoff: float = 1.0,
                                    max_backoff: float = 32.0,
                                    backoff_factor: float = 2.0) -> Optional[str]:
        """
        Call AI service with exponential backoff retry logic using native async calls
        and passing parameters via dictionary unpacking for google-genai SDK.

        Args:
            prompt: The prompt to send to the LLM
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff time in seconds
            max_backoff: Maximum backoff time in seconds
            backoff_factor: Multiplier for backoff delay

        Returns:
            Generated content as a string, or None on failure after retries.
        """
        # Ensure initialization (idempotent)
        if self.use_genai_sdk and self.genai_client is None:
            await self.initialize()
        elif not self.use_genai_sdk and self.llm is None:
            await self.initialize()

        # Ensure client is available
        if (self.use_genai_sdk and not self.genai_client) or \
            (not self.use_genai_sdk and not self.llm):
                logger.error("LLM client is not initialized. Cannot proceed.")
                return None

        backoff = initial_backoff
        start_time_overall = time.monotonic()
        logger.debug(f"Initiating LLM call via {'GenAI SDK' if self.use_genai_sdk else 'Vertex AI SDK'} (max_retries={max_retries}, model='{self.model_name}')")

        # --- Prepare Config Parameters ---
        genai_generation_params_dict = None # Dictionary for GenAI SDK + Vertex backend
        vertexai_generation_config = None # Typed object for Vertex AI SDK

        if self.use_genai_sdk:
            # Create dictionary of parameters expected directly by the API/SDK method
            genai_generation_params_dict = GenerateContentConfig(
                temperature=self.temperature,
                top_p=self.top_p,
                top_k=self.top_k,
                #max_output_token=1200,
                stop_sequences=self.stop_sequences if self.stop_sequences else None,
                presence_penalty=self.presence_penalty,
                frequency_penalty=self.frequency_penalty
                # Add other direct parameters if needed and supported
                # e.g., "candidate_count": 1
            )

            # Filter out None values
            #genai_generation_params_dict = {k: v for k, v in genai_generation_params_dict.items() if v is not None}
            logger.debug(f"GenAI SDK parameter dictionary: {genai_generation_params_dict}")
        else:
            # Vertex AI SDK uses the typed GenerationConfig object
            vertexai_generation_config = GenerationConfig(
                temperature=self.temperature, top_p=self.top_p, top_k=self.top_k,
                stop_sequences=self.stop_sequences, max_output_tokens=1200
            )
            logger.debug(f"Vertex AI SDK GenerationConfig object: {vertexai_generation_config}")
        # --- End Prepare Config ---

        for attempt in range(max_retries + 1):
            attempt_start_time = time.monotonic()
            log_prefix = f"LLM call attempt {attempt + 1}/{max_retries + 1}"
            logger.debug(f"{log_prefix} starting...")
            raw_response = None
            response_object = None

            try:
                if self.use_genai_sdk:
                    # --- *** THE CORRECTED CALL for google-genai SDK + Vertex backend *** ---
                    logger.debug(f"{log_prefix}: Calling genai_client.aio.models.generate_content with unpacked params...")
                    response_object = await self.genai_client.aio.models.generate_content(
                        model=f'{self.model_name}', # Ensure 'models/' prefix if needed
                        contents=[prompt],
                        config=genai_generation_params_dict
                    )
                    # --- *** END CORRECTED CALL *** ---

                    # --- Extract Text (GenAI SDK Response) ---
                    if response_object.candidates:
                        try:
                            raw_response = response_object.candidates[0].content.parts[0].text
                            logger.debug(f"{log_prefix}: Successfully extracted text.")
                        except (IndexError, AttributeError) as text_extract_err:
                            logger.warning(f"{log_prefix}: Could not extract text: {text_extract_err}. Candidate: {response_object.candidates[0]}")
                            raw_response = None
                    else:
                        safety_ratings = getattr(getattr(response_object, 'prompt_feedback', None), 'safety_ratings', 'N/A')
                        logger.warning(f"{log_prefix}: Response had no candidates. Safety: {safety_ratings}")
                        raw_response = None
                    # --- End Extract Text ---

                else: # Use Vertex AI SDK
                    # This path remains the same, using the typed config object
                    logger.debug(f"{log_prefix}: Calling llm.generate_content_async with GenerationConfig object...")
                    response_object = await self.llm.generate_content_async(
                        contents=[prompt],
                        generation_config=vertexai_generation_config,
                        stream=False
                    )
                    # --- Extract Text (Vertex AI SDK Response) ---
                    if response_object.candidates:
                            try:
                                raw_response = response_object.candidates[0].content.text
                                logger.debug(f"{log_prefix}: Successfully extracted text.")
                            except (IndexError, AttributeError) as text_extract_err:
                                logger.warning(f"{log_prefix}: Could not extract text: {text_extract_err}. Candidate: {response_object.candidates[0]}")
                                raw_response = None
                    else:
                        safety_ratings = getattr(getattr(response_object, 'prompt_feedback', None), 'safety_ratings', 'N/A')
                        logger.warning(f"{log_prefix}: Response had no candidates. Safety: {safety_ratings}")
                        raw_response = None
                        # --- End Extract Text ---

                # --- Attempt Succeeded ---
                attempt_duration = time.monotonic() - attempt_start_time
                logger.debug(f"{log_prefix} completed in {attempt_duration:.3f}s.")

                if raw_response is not None:
                    overall_duration = time.monotonic() - start_time_overall
                    final_response = raw_response.strip()
                    logger.debug(f"LLM call successful after {overall_duration:.3f}s total. Length: {len(final_response)}. Snippet: {final_response[:100]}...")
                    return final_response
                else:
                    # Treat no content as a failure for retry purposes
                    raise ValueError("Response received but no valid content extracted (e.g., safety filters).")


            except Exception as e:
                # ... (Keep existing exception handling logic: check rate limit, log, retry/fail, return None) ...
                attempt_duration = time.monotonic() - attempt_start_time
                error_message = str(e)
                logger.warning(f"{log_prefix} failed in {attempt_duration:.3f}s: {error_message}")

                is_rate_limit = ("429" in error_message or "quota" in error_message.lower() or
                                    "rate limit" in error_message.lower() or "resource exhausted" in error_message.lower())

                if is_rate_limit and attempt < max_retries:
                    jitter = random.uniform(0, 0.25 * backoff)
                    sleep_time = backoff + jitter
                    logger.info(f"{log_prefix}: Rate limit/resource error. Retrying in {sleep_time:.2f}s...")
                    await asyncio.sleep(sleep_time)
                    backoff = min(backoff * backoff_factor, max_backoff)
                else:
                    if is_rate_limit:
                            logger.error(f"{log_prefix}: Max retries ({max_retries + 1}) reached for rate limit/resource errors.")
                    else: # Log other errors with traceback
                            logger.error(f"{log_prefix}: Non-retryable error: {e}", exc_info=True)
                    return None # Return None on definitive failure

        # Should only be reached if all retries failed
        overall_duration = time.monotonic() - start_time_overall
        logger.error(f"LLM call failed definitively after {max_retries + 1} attempts. Total time: {overall_duration:.3f}s")
        return None