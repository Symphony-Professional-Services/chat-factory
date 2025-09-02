"""
Strategy pattern implementations for different conversation generation approaches.
"""

from typing import Dict, Type, Any
from .base import TaxonomyStrategy, GenerationStrategy, FewShotExampleStrategy

# Import strategy implementations
from .financial_advisory import FinancialAdvisoryTaxonomyStrategy, FinancialAdvisoryGenerationStrategy
from .few_shot import BasicFewShotStrategy
from .company_tagging import CompanyTaggingTaxonomyStrategy, CompanyTaggingGenerationStrategy

# Registry of available strategies
TAXONOMY_STRATEGIES: Dict[str, Type[TaxonomyStrategy]] = {
    "financial_advisory": FinancialAdvisoryTaxonomyStrategy,
    "company_tagging": CompanyTaggingTaxonomyStrategy
}

GENERATION_STRATEGIES: Dict[str, Type[GenerationStrategy]] = {
    "financial_advisory": FinancialAdvisoryGenerationStrategy,
    "company_tagging": CompanyTaggingGenerationStrategy
}

FEW_SHOT_STRATEGIES: Dict[str, Type[FewShotExampleStrategy]] = {
    "basic": BasicFewShotStrategy
}


def register_taxonomy_strategy(name: str, strategy_cls: Type[TaxonomyStrategy]):
    """Register a taxonomy strategy."""
    TAXONOMY_STRATEGIES[name] = strategy_cls


def register_generation_strategy(name: str, strategy_cls: Type[GenerationStrategy]):
    """Register a generation strategy."""
    GENERATION_STRATEGIES[name] = strategy_cls


def register_few_shot_strategy(name: str, strategy_cls: Type[FewShotExampleStrategy]):
    """Register a few-shot example strategy."""
    FEW_SHOT_STRATEGIES[name] = strategy_cls


def create_taxonomy_strategy(strategy_name: str, config: Any) -> TaxonomyStrategy:
    """Factory function to create a taxonomy strategy."""
    if strategy_name not in TAXONOMY_STRATEGIES:
        raise ValueError(f"Unknown taxonomy strategy: {strategy_name}")
    return TAXONOMY_STRATEGIES[strategy_name](config)


def create_generation_strategy(strategy_name: str, config: Any) -> GenerationStrategy:
    """Factory function to create a generation strategy."""
    if strategy_name not in GENERATION_STRATEGIES:
        raise ValueError(f"Unknown generation strategy: {strategy_name}")
    return GENERATION_STRATEGIES[strategy_name](config)


def create_few_shot_strategy(strategy_name: str, config: Any) -> FewShotExampleStrategy:
    """Factory function to create a few-shot example strategy."""
    if strategy_name not in FEW_SHOT_STRATEGIES:
        raise ValueError(f"Unknown few-shot example strategy: {strategy_name}")
    return FEW_SHOT_STRATEGIES[strategy_name](config)