"""
Text formatter using Anthropic API to convert technical expressions to readable English.
Converts raw database content with conditional logic into natural language.
"""

import os
import sys
import logging
from typing import Optional
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.adaptive_model_selector import create_adaptive_selector

load_dotenv()

logger = logging.getLogger(__name__)


class TextFormatter:
    """Formats technical database content into readable English using Claude."""

    def __init__(self, model_tier: str = "fast"):
        """
        Initialize the text formatter.

        Args:
            model_tier: Model tier ('fast', 'balanced', 'powerful') for adaptive selection
        """
        self.model_tier = model_tier
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.client = None
        self.model_selector = None
        self.available = False

        self._init_client()

    def _init_client(self) -> bool:
        """
        Initialize Anthropic client.

        Returns:
            True if client initialized successfully, False otherwise
        """
        if self.available:
            return True

        if not self.api_key:
            logger.warning("ANTHROPIC_API_KEY not found in environment - text formatting unavailable")
            return False

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            # Create adaptive model selector
            self.model_selector = create_adaptive_selector(self.client, tier=self.model_tier)
            self.available = True
            logger.info(f"✓ Text formatter initialized with tier: {self.model_tier}")
            return True
        except Exception as e:
            logger.error(f"Could not initialize Anthropic client: {e}")
            return False

    def format_parameter_value(self, raw_value: str, param_type: str, program_name: str) -> str:
        """
        Convert raw database parameter value to readable English.

        Args:
            raw_value: Raw database content (may contain technical expressions)
            param_type: Type of parameter (e.g., 'reserves', 'occupancy')
            program_name: Name of the loan program

        Returns:
            Formatted English text, or raw_value if formatting fails
        """
        if not self._init_client():
            return raw_value  # Fall back to raw value if API unavailable

        # Skip formatting for simple values
        if len(raw_value) < 50 and not any(keyword in raw_value.lower() for keyword in ['if', 'then', '>=', '<=', '=']):
            return raw_value

        try:
            prompt = f"""Convert this technical database expression into clear, well-structured English sentences for a loan officer or borrower.

Program: {program_name}
Parameter Type: {param_type.replace('_', ' ').title()}
Raw Expression:
{raw_value}

Instructions:
- Convert technical conditions (if/then, >=, <=, etc.) into natural language
- Break down complex logic into bullet points or numbered lists if needed
- Use clear, professional language suitable for loan officers
- Explain thresholds, conditions, and requirements clearly
- Keep the formatting clean and readable
- Do NOT add information that isn't in the original expression

Output ONLY the formatted English text with no preamble or explanation."""

            message, model_used = self.model_selector.call_with_fallback(
                max_tokens=500,
                temperature=0.2,  # Low temperature for consistency
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            logger.info(f"Text formatting used model: {model_used}")

            if not message.content or len(message.content) == 0:
                logger.warning("Claude returned empty response")
                return raw_value

            formatted = message.content[0].text.strip()

            if not formatted:
                logger.warning("Could not extract formatted text from Claude response")
                return raw_value

            logger.info(f"✓ Formatted {param_type} for {program_name}")
            return formatted

        except Exception as e:
            logger.error(f"Error formatting parameter value: {e}")
            return raw_value  # Fall back to raw value on error


# Singleton instance
_formatter: Optional[TextFormatter] = None


def get_formatter() -> TextFormatter:
    """
    Get singleton instance of TextFormatter.
    Lazy initialization on first call.
    """
    global _formatter
    if _formatter is None:
        _formatter = TextFormatter()
    return _formatter
