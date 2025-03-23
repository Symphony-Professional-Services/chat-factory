"""LLM providers for Chat Factory."""

import logging
from typing import Dict, Type, Any
from .base import LLMProvider
from .mock import MockLLMProvider

# Registry of available LLM providers
LLM_PROVIDERS: Dict[str, Type[LLMProvider]] = {
    "mock": MockLLMProvider
}

# Import VertexAI provider if available, otherwise log warning
try:
    from .vertex_ai import VertexAIProvider, USING_GENAI_SDK
    LLM_PROVIDERS["vertex_ai"] = VertexAIProvider
    
    if USING_GENAI_SDK:
        logging.info("GenAI SDK is available. Gemini 2.0 models are supported.")
    else:
        logging.info("Only Vertex AI SDK is available. Gemini 1.5 models are supported.")
except ImportError:
    logging.warning("VertexAI provider not available (neither vertexai nor google-genai package is installed). "
                  "Only mock provider will be available.")


def create_llm_provider(provider_name: str, config: Any) -> LLMProvider:
    """
    Factory function to create an LLM provider.
    
    Args:
        provider_name: Name of the provider to create
        config: Configuration for the provider
        
    Returns:
        LLMProvider instance
    """
    if provider_name not in LLM_PROVIDERS:
        raise ValueError(f"Unknown LLM provider: {provider_name}")
    return LLM_PROVIDERS[provider_name](config)