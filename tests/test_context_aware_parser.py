"""
Unit tests for context_aware_parser.py
Tests the context-aware query parser with Anthropic tool calling.
"""

import pytest
import os
from unittest.mock import Mock, MagicMock, patch
from src.context_aware_parser import ContextAwareParser


@pytest.mark.unit
class TestContextAwareParser:
    """Test suite for ContextAwareParser class."""

    def test_initialization_without_api_key(self, test_db_path, temp_scratchpad, monkeypatch):
        """Test parser initialization when ANTHROPIC_API_KEY is missing."""
        # Remove API key from environment
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        parser = ContextAwareParser(db_path=test_db_path)

        assert parser.anthropic is None
        assert parser.db_path == test_db_path
        assert len(parser.db_columns) > 0
        assert len(parser.script_tools) > 0

    @pytest.mark.requires_api_key
    def test_initialization_with_api_key(self, test_db_path, mock_env_with_api_key):
        """Test parser initialization with ANTHROPIC_API_KEY set."""
        with patch('src.context_aware_parser.Anthropic') as mock_anthropic:
            parser = ContextAwareParser(db_path=test_db_path)

            assert parser.anthropic is not None
            mock_anthropic.assert_called_once()

    def test_get_database_columns(self, test_db_path):
        """Test database column retrieval from actual database."""
        parser = ContextAwareParser(db_path=test_db_path)

        # Verify parser found columns from actual database
        assert len(parser.db_columns) > 0

        # Verify essential core columns exist (these should always be in programs_v3)
        essential_columns = [
            'loan_servicer', 'program_name', 'citizenship',
            'occupancy', 'ltv'
        ]

        assert all(col in parser.db_columns for col in essential_columns)

    def test_build_script_tools(self, test_db_path, monkeypatch):
        """Test script tool definitions are correctly built."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        parser = ContextAwareParser(db_path=test_db_path)

        tools = parser.script_tools

        # Should have 3 tools
        assert len(tools) == 3

        # Check tool names
        tool_names = [tool['name'] for tool in tools]
        assert 'find_param_across_programs' in tool_names
        assert 'show_program_parameters' in tool_names
        assert 'match_programs' in tool_names

        # Check find_param_across_programs tool structure
        param_tool = next(t for t in tools if t['name'] == 'find_param_across_programs')
        assert 'input_schema' in param_tool
        assert 'properties' in param_tool['input_schema']
        assert 'param_name' in param_tool['input_schema']['properties']
        assert 'loan_servicer' in param_tool['input_schema']['properties']

    def test_map_param_name_direct_match(self, test_db_path, monkeypatch):
        """Test parameter name mapping with direct match."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        parser = ContextAwareParser(db_path=test_db_path)

        assert parser._map_param_name('citizenship') == 'citizenship'
        assert parser._map_param_name('ltv') == 'ltv'

    def test_map_param_name_alias(self, test_db_path, monkeypatch):
        """Test parameter name mapping with aliases."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        parser = ContextAwareParser(db_path=test_db_path)

        assert parser._map_param_name('appraisal') == 'appraisal_requirements'
        assert parser._map_param_name('reserves') == 'reserves'
        assert parser._map_param_name('docs') == 'income_documentation'

    def test_map_param_name_fuzzy_match(self, test_db_path, monkeypatch):
        """Test parameter name mapping with fuzzy matching."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        parser = ContextAwareParser(db_path=test_db_path)

        # Fuzzy match should work for close matches
        result = parser._map_param_name('occupanc')
        assert result == 'occupancy'

    @pytest.mark.requires_api_key
    def test_parse_query_with_context(self, test_db_path, temp_scratchpad, mock_env_with_api_key):
        """Test query parsing with context parameters."""
        with patch('src.context_aware_parser.Anthropic') as mock_anthropic_class:
            # Setup mock Anthropic response
            mock_client = MagicMock()
            mock_anthropic_class.return_value = mock_client

            mock_tool_use = MagicMock()
            mock_tool_use.type = "tool_use"
            mock_tool_use.name = "find_param_across_programs"
            mock_tool_use.input = {
                "param_name": "citizenship",
                "loan_servicer": "Prime"
            }

            mock_message = MagicMock()
            mock_message.content = [mock_tool_use]
            mock_client.messages.create.return_value = mock_message

            parser = ContextAwareParser(db_path=test_db_path)

            result = parser.parse_query_with_context(
                "What are the citizenship requirements?",
                selected_programs=["PRMG/Prime Connect"],
                selected_servicers=["Prime"]
            )

            assert result['script_name'] == 'find_param_across_programs'
            assert result['parameters']['param_name'] == 'citizenship'
            assert result['parameters']['loan_servicer'] == 'Prime'
            assert result['confidence'] == 0.95

    def test_parse_query_without_anthropic(self, test_db_path, temp_scratchpad, monkeypatch):
        """Test query parsing when Anthropic client is not available."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        parser = ContextAwareParser(db_path=test_db_path)

        result = parser.parse_query_with_context(
            "What are the citizenship requirements?",
            selected_programs=["PRMG/Prime Connect"],
            selected_servicers=["Prime"]
        )

        assert result['script_name'] is None
        assert 'error' in result
        assert 'Anthropic API not available' in result['error']

    @pytest.mark.requires_db
    def test_execute_script(self, test_db_path, temp_scratchpad, monkeypatch):
        """Test script execution with parameters."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("SCRATCHPAD_PATH", temp_scratchpad)

        parser = ContextAwareParser(db_path=test_db_path)

        # Execute find_param_across_programs script
        success = parser.execute_script(
            'find_param_across_programs',
            {
                'param_name': 'citizenship',
                'loan_servicer': 'Prime'
            }
        )

        assert success is True

        # Check scratchpad output
        with open(temp_scratchpad, 'r') as f:
            output = f.read()
            assert len(output) > 0

    def test_execute_script_not_found(self, test_db_path, temp_scratchpad, monkeypatch):
        """Test execution of non-existent script."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("SCRATCHPAD_PATH", temp_scratchpad)

        parser = ContextAwareParser(db_path=test_db_path)

        success = parser.execute_script('nonexistent_script', {})

        assert success is False

        # Check error message in scratchpad
        with open(temp_scratchpad, 'r') as f:
            output = f.read()
            assert 'not found' in output.lower()

    @pytest.mark.requires_db
    def test_parse_and_execute_removes_prefix(self, test_db_path, temp_scratchpad, mock_env_with_api_key, monkeypatch):
        """Test that ^ prefix is removed from query before processing."""
        with patch('src.context_aware_parser.Anthropic') as mock_anthropic_class:
            mock_client = MagicMock()
            mock_anthropic_class.return_value = mock_client

            # Setup mock for successful parsing
            mock_tool_use = MagicMock()
            mock_tool_use.type = "tool_use"
            mock_tool_use.name = "match_programs"
            mock_tool_use.input = {}

            mock_message = MagicMock()
            mock_message.content = [mock_tool_use]
            mock_client.messages.create.return_value = mock_message

            parser = ContextAwareParser(db_path=test_db_path)
            monkeypatch.setenv("SCRATCHPAD_PATH", temp_scratchpad)

            # Query with ^ prefix
            success = parser.parse_and_execute("^ match programs")

            # Should still succeed after removing prefix
            mock_client.messages.create.assert_called_once()
            call_args = mock_client.messages.create.call_args
            query_in_message = call_args[1]['messages'][0]['content']
            assert '^' not in query_in_message

    def test_tool_definitions_have_required_fields(self, test_db_path, monkeypatch):
        """Test that all tool definitions have required fields."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        parser = ContextAwareParser(db_path=test_db_path)

        for tool in parser.script_tools:
            assert 'name' in tool
            assert 'description' in tool
            assert 'input_schema' in tool
            assert 'type' in tool['input_schema']
            assert tool['input_schema']['type'] == 'object'
            assert 'properties' in tool['input_schema']
