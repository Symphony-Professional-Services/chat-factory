"""
Company tagging strategies package.

This package contains the implementation of strategies specific to company tagging use cases.
"""

from .taxonomy_strategy import CompanyTaggingTaxonomyStrategy
from .generation_strategy import CompanyTaggingGenerationStrategy

__all__ = ['CompanyTaggingTaxonomyStrategy', 'CompanyTaggingGenerationStrategy']