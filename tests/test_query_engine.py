"""
Unit tests for query_engine.py
Tests the QueryEngine class for FastAPI integration.
"""

import pytest
import os
import sys
import json
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Add web-app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "web-app"))

import query_engine
QueryEngine = query_engine.QueryEngine
get_query_engine = query_engine.get_query_engine


@pytest.mark.unit
class TestQueryEngine:
    """Test suite for QueryEngine class."""

    def test_initialization(self, test_db_path, monkeypatch):
        """Test QueryEngine initialization."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        assert engine.db_path == test_db_path
        assert engine.parser is not None
        assert Path(engine.scratchpad_path).name == '.scratchpad_web'

    def test_initialization_missing_database(self):
        """Test initialization fails with missing database."""
        with pytest.raises(FileNotFoundError):
            QueryEngine(db_path="/nonexistent/path/to/db.db")

    @pytest.mark.requires_db
    def test_execute_query_simple(self, test_db_path, monkeypatch):
        """Test simple query execution."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        # Mock parser to return success
        with patch.object(engine.parser, 'parse_and_execute', return_value=True):
            # Mock scratchpad file
            scratchpad_content = "PRMG/Prime Connect: Result data"
            with open(engine.scratchpad_path, 'w') as f:
                f.write(scratchpad_content)

            result = engine.execute_query("test query")

            assert result['success'] is True
            assert result['query'] == '^ test query'
            assert scratchpad_content in result['results']
            assert 'executedAt' in result

    @pytest.mark.requires_db
    def test_execute_query_with_context(self, test_db_path, sample_context_params, monkeypatch):
        """Test query execution with context parameters."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        # Track if QUERY_CONTEXT was set during execution
        context_was_set = {'value': False}

        def check_context_during_execution(*args, **kwargs):
            context_was_set['value'] = 'QUERY_CONTEXT' in os.environ
            return True

        with patch.object(engine.parser, 'parse_and_execute', side_effect=check_context_during_execution) as mock_exec:
            # Mock scratchpad
            with open(engine.scratchpad_path, 'w') as f:
                f.write("Test results")

            result = engine.execute_query("test query", sample_context_params)

            assert result['success'] is True
            # Verify context was set during execution (before cleanup)
            assert context_was_set['value'] is True

    @pytest.mark.requires_db
    def test_execute_query_with_prefix(self, test_db_path, monkeypatch):
        """Test query execution preserves ^ prefix if present."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        with patch.object(engine.parser, 'parse_and_execute', return_value=True):
            with open(engine.scratchpad_path, 'w') as f:
                f.write("Results")

            result = engine.execute_query("^ already has prefix")

            assert result['query'] == '^ already has prefix'

    @pytest.mark.requires_db
    def test_execute_query_failure(self, test_db_path, monkeypatch):
        """Test query execution when parser fails."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        with patch.object(engine.parser, 'parse_and_execute', return_value=False):
            with open(engine.scratchpad_path, 'w') as f:
                f.write("Error: Query failed")

            result = engine.execute_query("failing query")

            assert result['success'] is False
            assert 'Error' in result['results'] or 'failed' in result['results']

    @pytest.mark.requires_db
    def test_execute_query_exception(self, test_db_path, monkeypatch):
        """Test query execution handles exceptions gracefully."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        with patch.object(engine.parser, 'parse_and_execute', side_effect=Exception("Test error")):
            result = engine.execute_query("error query")

            assert result['success'] is False
            assert 'Test error' in result['results']

    @pytest.mark.requires_db
    def test_get_available_scripts(self, test_db_path, monkeypatch):
        """Test fetching available scripts from database."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        scripts = engine.get_available_scripts()

        assert isinstance(scripts, list)
        assert len(scripts) > 0

        # Check script structure
        script = scripts[0]
        assert 'name' in script
        assert 'description' in script
        assert 'prompt' in script

    @pytest.mark.requires_db
    def test_check_health(self, test_db_path, monkeypatch):
        """Test health check returns correct status."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        health = engine.check_health()

        assert 'available' in health
        assert health['available'] is True
        assert 'scriptCount' in health
        assert health['scriptCount'] > 0
        assert health.get('error') is None

    @pytest.mark.requires_db
    def test_fetch_program_details(self, test_db_path, monkeypatch):
        """Test fetching program details from database."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        details = engine.fetch_program_details(
            programs=["PRMG/Prime Connect", "PRMG/Plus Connect"],
            servicer="Prime"
        )

        assert isinstance(details, dict)
        assert "PRMG/Prime Connect" in details
        assert "PRMG/Plus Connect" in details

        # Check structure
        program_detail = details["PRMG/Prime Connect"]
        assert 'program_summary' in program_detail
        assert 'borrower_credit_score' in program_detail

    @pytest.mark.requires_db
    def test_fetch_program_parameter(self, test_db_path, monkeypatch):
        """Test fetching specific parameter for a program."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        value = engine.fetch_program_parameter(
            program_name="PRMG/Prime Connect",
            servicer="Prime",
            param_name="citizenship"
        )

        assert value is not None
        assert isinstance(value, str)
        assert len(value) > 0

    @pytest.mark.requires_db
    def test_fetch_program_parameter_missing(self, test_db_path, monkeypatch):
        """Test fetching parameter for non-existent program."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        value = engine.fetch_program_parameter(
            program_name="NonExistent/Program",
            servicer="Prime",
            param_name="citizenship"
        )

        assert value is None

    def test_singleton_pattern(self, test_db_path, monkeypatch):
        """Test get_query_engine returns singleton instance."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        # Mock the default db path
        with patch('query_engine.QueryEngine') as MockEngine:
            mock_instance = MagicMock()
            MockEngine.return_value = mock_instance

            # Reset singleton
            query_engine._query_engine = None

            # First call creates instance
            engine1 = get_query_engine()
            # Second call returns same instance
            engine2 = get_query_engine()

            # Should be called only once
            assert MockEngine.call_count == 1


@pytest.mark.unit
class TestQueryEngineContextHandling:
    """Test context parameter handling in QueryEngine."""

    @pytest.mark.requires_db
    def test_context_params_with_selected_programs(self, test_db_path, monkeypatch):
        """Test context parameters are properly extracted from selected programs."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        context_params = {
            'selected_programs': ['PRMG/Prime Connect', 'PRMG/Plus Connect'],
            'selected_servicers': ['Prime']
        }

        # Capture context during execution
        captured_context = {'value': None}

        def capture_context_during_execution(*args, **kwargs):
            if 'QUERY_CONTEXT' in os.environ:
                captured_context['value'] = json.loads(os.environ['QUERY_CONTEXT'])
            return True

        with patch.object(engine.parser, 'parse_and_execute', side_effect=capture_context_during_execution):
            with open(engine.scratchpad_path, 'w') as f:
                f.write("Results")

            result = engine.execute_query("test", context_params)

            # Check QUERY_CONTEXT was set correctly during execution
            assert captured_context['value'] is not None
            assert 'selected_programs' in captured_context['value']
            assert 'selected_servicers' in captured_context['value']

    @pytest.mark.requires_db
    def test_context_cleanup(self, test_db_path, monkeypatch):
        """Test that context is cleaned up from environment after execution."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = QueryEngine(db_path=test_db_path, use_llm=False)

        with patch.object(engine.parser, 'parse_and_execute', return_value=True):
            with open(engine.scratchpad_path, 'w') as f:
                f.write("Results")

            engine.execute_query("test", {'selected_programs': ['Test']})

            # Context should be removed after execution
            assert 'QUERY_CONTEXT' not in os.environ
