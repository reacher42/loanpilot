#!/usr/bin/env python3
"""
Adaptive model selector for Anthropic API calls.
Provides automatic fallback when models are deprecated or unavailable.
Ensures API calls never fail due to model deprecation.
"""

import os
import logging
from typing import Optional, Tuple, List
from anthropic import Anthropic, APIError

logger = logging.getLogger(__name__)


class AdaptiveModelSelector:
    """
    Handles automatic model selection with fallback chain.
    Tries models in priority order until one succeeds.
    """

    # Model fallback chains by capability tier
    # Each list is ordered from newest/preferred to most stable/fallback
    # Updated 2025-11-08 with current valid models - using aliases for auto-updates
    MODEL_CHAINS = {
        'fast': [
            'claude-haiku-4-5',             # Latest Haiku 4.5 (fast, cost-effective) - auto-updates
            'claude-3-5-haiku-latest',      # Haiku 3.5 fallback - auto-updates
            'claude-3-haiku-20240307',      # Stable Haiku 3 fallback (specific version)
        ],
        'balanced': [
            'claude-sonnet-4-5',            # Latest Sonnet 4.5 (best balanced) - auto-updates
            'claude-3-7-sonnet-latest',     # Sonnet 3.7 fallback - auto-updates
            'claude-sonnet-4-0',            # Sonnet 4.0 fallback alias
        ],
        'powerful': [
            'claude-opus-4-1',              # Latest Opus 4.1 (most capable) - auto-updates
            'claude-opus-4-0',              # Opus 4.0 fallback alias
            'claude-sonnet-4-5',            # Sonnet 4.5 as final fallback
        ]
    }

    def __init__(self, client: Anthropic, tier: str = 'fast'):
        """
        Initialize adaptive model selector.

        Args:
            client: Initialized Anthropic client
            tier: Model tier - 'fast', 'balanced', or 'powerful'
        """
        self.client = client
        self.tier = tier
        self.successful_model: Optional[str] = None
        self.failed_models: List[str] = []

        # Allow environment variable override for model chain
        env_model = os.getenv('ANTHROPIC_MODEL')
        if env_model:
            logger.info(f"Using environment-specified model: {env_model}")
            self.model_chain = [env_model] + self.MODEL_CHAINS.get(tier, self.MODEL_CHAINS['fast'])
        else:
            self.model_chain = self.MODEL_CHAINS.get(tier, self.MODEL_CHAINS['fast'])

        logger.info(f"Initialized adaptive model selector with tier '{tier}'")
        logger.info(f"Fallback chain: {' → '.join(self.model_chain)}")

    def get_working_model(self, test_call: bool = False) -> str:
        """
        Get a working model, testing with fallback if needed.

        Args:
            test_call: If True, make a test API call to verify model works

        Returns:
            Model name that is working

        Raises:
            RuntimeError: If all models in chain fail
        """
        # If we already found a working model, use it
        if self.successful_model:
            return self.successful_model

        # Try each model in the chain
        for model in self.model_chain:
            if model in self.failed_models:
                continue  # Skip known failed models

            if test_call:
                # Test the model with a simple API call
                if self._test_model(model):
                    self.successful_model = model
                    logger.info(f"✓ Selected working model: {model}")
                    return model
                else:
                    self.failed_models.append(model)
                    logger.warning(f"✗ Model {model} failed test call, trying next...")
            else:
                # Optimistically return the first model without testing
                # Will be verified on actual use
                self.successful_model = model
                logger.info(f"Selected model (no pre-test): {model}")
                return model

        # All models failed
        raise RuntimeError(
            f"All models in {self.tier} tier failed: {', '.join(self.model_chain)}"
        )

    def _test_model(self, model: str) -> bool:
        """
        Test if a model is working with a minimal API call.

        Args:
            model: Model name to test

        Returns:
            True if model works, False otherwise
        """
        try:
            response = self.client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            return response is not None and len(response.content) > 0
        except APIError as e:
            # Check if it's a model deprecation error
            error_msg = str(e).lower()
            is_model_error = (
                'model' in error_msg and (
                    'deprecated' in error_msg or
                    'not found' in error_msg or
                    'not_found' in error_msg  # Handle not_found_error
                )
            )
            if is_model_error:
                logger.warning(f"Model {model} is deprecated or not found: {e}")
                return False
            # Other API errors might be transient, so we don't mark as failed
            logger.error(f"API error testing model {model}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing model {model}: {e}")
            return False

    def call_with_fallback(self, **kwargs) -> Tuple[any, str]:
        """
        Make an Anthropic API call with automatic model fallback.

        Args:
            **kwargs: Arguments to pass to client.messages.create()
                      (model will be overridden by fallback chain)

        Returns:
            Tuple of (response, model_used)

        Raises:
            RuntimeError: If all models fail
        """
        last_error = None

        for model in self.model_chain:
            if model in self.failed_models:
                continue

            try:
                logger.info(f"Attempting API call with model: {model}")
                kwargs['model'] = model
                response = self.client.messages.create(**kwargs)

                # Success! Mark this model as working
                self.successful_model = model
                logger.info(f"✓ API call succeeded with model: {model}")
                return response, model

            except APIError as e:
                error_msg = str(e).lower()

                # Check for model deprecation/not found errors
                # Handle both "not found" and "not_found_error" formats
                is_model_error = (
                    'model' in error_msg and (
                        'deprecated' in error_msg or
                        'not found' in error_msg or
                        'not_found' in error_msg or  # Handle not_found_error
                        'invalid' in error_msg
                    )
                )

                if is_model_error:
                    logger.warning(f"✗ Model {model} deprecated/unavailable: {e}")
                    self.failed_models.append(model)
                    last_error = e
                    continue  # Try next model

                # For other API errors, re-raise immediately (don't try fallback)
                logger.error(f"API error (not model-related): {e}")
                raise

            except Exception as e:
                # Unexpected error - log and try next model
                logger.error(f"Unexpected error with model {model}: {e}")
                self.failed_models.append(model)
                last_error = e
                continue

        # All models failed
        raise RuntimeError(
            f"All models in {self.tier} tier failed. Last error: {last_error}"
        )


def create_adaptive_selector(client: Anthropic, tier: str = 'fast') -> AdaptiveModelSelector:
    """
    Factory function to create an adaptive model selector.

    Args:
        client: Initialized Anthropic client
        tier: Model tier - 'fast', 'balanced', or 'powerful'

    Returns:
        AdaptiveModelSelector instance
    """
    return AdaptiveModelSelector(client, tier)


def get_model_for_tier(tier: str = 'fast') -> str:
    """
    Get the preferred model for a tier without making API calls.
    Useful for initialization.

    Args:
        tier: Model tier - 'fast', 'balanced', or 'powerful'

    Returns:
        Model name (first in chain for that tier)
    """
    # Check environment override first
    env_model = os.getenv('ANTHROPIC_MODEL')
    if env_model:
        return env_model

    chain = AdaptiveModelSelector.MODEL_CHAINS.get(tier, AdaptiveModelSelector.MODEL_CHAINS['fast'])
    return chain[0]
