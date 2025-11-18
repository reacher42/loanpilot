"""
Pytest fixtures and configuration for LoanPilot tests.
Provides shared test fixtures, mock data, and test database setup.
"""

import os
import sys
import tempfile
import sqlite3
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock
from typing import Generator

# Add project paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "web-app"))


@pytest.fixture(scope="session")
def test_db_path() -> Generator[str, None, None]:
    """Use the actual loanpilot.db database for testing."""
    # Point to the actual database in project root
    db_path = str(project_root / "loanpilot.db")

    # Verify database exists
    if not Path(db_path).exists():
        raise FileNotFoundError(f"Database not found at {db_path}. Please ensure loanpilot.db exists.")

    yield db_path
    # No cleanup - we're using the real database


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client for testing without real API calls."""
    mock_client = MagicMock()

    # Mock messages.create for tool calling
    mock_message = MagicMock()
    mock_tool_use = MagicMock()
    mock_tool_use.type = "tool_use"
    mock_tool_use.name = "find_param_across_programs"
    mock_tool_use.input = {
        "param_name": "citizenship",
        "loan_servicer": "Prime"
    }
    mock_message.content = [mock_tool_use]
    mock_client.messages.create.return_value = mock_message

    return mock_client


@pytest.fixture
def mock_env_with_api_key(monkeypatch):
    """Set mock ANTHROPIC_API_KEY in environment."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-key-123456789")


@pytest.fixture
def sample_context_params():
    """Sample context parameters for query testing."""
    return {
        "selected_programs": ["PRMG/Prime Connect", "PRMG/Plus Connect"],
        "selected_servicers": ["Prime"]
    }


@pytest.fixture
def sample_query_results():
    """Sample query results for parser testing."""
    return """
PRMG/Prime Connect: U.S. Citizen, Permanent Resident
PRMG/Plus Connect: U.S. Citizen
"""


@pytest.fixture
def temp_scratchpad() -> Generator[str, None, None]:
    """Create temporary scratchpad file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.scratchpad', delete=False) as tmp:
        scratchpad_path = tmp.name

    yield scratchpad_path

    # Cleanup
    try:
        os.unlink(scratchpad_path)
    except:
        pass


@pytest.fixture
def mock_db_columns():
    """Mock database column list."""
    return [
        "id", "loan_servicer", "program_name", "program_summary",
        "borrower_credit_score", "loan_amount", "ltv", "dti",
        "transaction_type", "occupancy", "citizenship",
        "appraisal_requirements", "reserves", "income_documentation"
    ]


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables before each test."""
    # Store original values
    original_db_path = os.environ.get('DB_PATH')
    original_scratchpad = os.environ.get('SCRATCHPAD_PATH')
    original_api_key = os.environ.get('ANTHROPIC_API_KEY')

    yield

    # Restore original values
    if original_db_path:
        os.environ['DB_PATH'] = original_db_path
    elif 'DB_PATH' in os.environ:
        del os.environ['DB_PATH']

    if original_scratchpad:
        os.environ['SCRATCHPAD_PATH'] = original_scratchpad
    elif 'SCRATCHPAD_PATH' in os.environ:
        del os.environ['SCRATCHPAD_PATH']

    if original_api_key:
        os.environ['ANTHROPIC_API_KEY'] = original_api_key
    elif 'ANTHROPIC_API_KEY' in os.environ:
        del os.environ['ANTHROPIC_API_KEY']
