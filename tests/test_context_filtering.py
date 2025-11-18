"""
End-to-end tests for context-aware query filtering.
Verifies that text queries properly filter results based on selected programs.
"""

import pytest
import sys
import os
from pathlib import Path

# Add web-app to path
sys.path.insert(0, str(Path(__file__).parent.parent / "web-app"))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import query_engine
from context_aware_parser import ContextAwareParser


@pytest.mark.integration
class TestContextAwareFiltering:
    """Test that queries respect selected program context."""

    @pytest.mark.requires_db
    def test_query_filters_by_selected_programs(self, test_db_path, monkeypatch):
        """
        Test that a parameter query only returns data for selected programs.
        This is the critical end-to-end test for context filtering.
        """
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        # Create engine and parser
        engine = query_engine.QueryEngine(db_path=test_db_path, use_llm=False)
        parser = ContextAwareParser(db_path=test_db_path)

        # Manually execute the find_param_across_programs script with context
        # Simulating what happens when user has selected specific programs
        selected_programs = ["PRMG/Prime Connect"]

        parameters = {
            'param_name': 'citizenship',
            'loan_servicer': 'Prime',
            'selected_programs': selected_programs
        }

        success = parser.execute_script('find_param_across_programs', parameters)

        assert success is True

        # Read results from scratchpad
        with open(engine.scratchpad_path, 'r') as f:
            results = f.read()

        # Verify results contain ONLY the selected program
        assert 'PRMG/Prime Connect' in results

        # Verify results DO NOT contain other Prime programs
        assert 'PRMG/Plus Connect' not in results

        # Verify the filtering message is present
        assert 'Filtered by Selected Programs: 1' in results or 'Selected Programs' in results

    @pytest.mark.requires_db
    def test_query_returns_all_when_no_context(self, test_db_path, monkeypatch):
        """
        Test that without selected programs, query returns all programs for servicer.
        """
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = query_engine.QueryEngine(db_path=test_db_path, use_llm=False)
        parser = ContextAwareParser(db_path=test_db_path)

        # Execute WITHOUT selected_programs
        parameters = {
            'param_name': 'citizenship',
            'loan_servicer': 'Prime'
            # NO selected_programs key
        }

        success = parser.execute_script('find_param_across_programs', parameters)

        assert success is True

        # Read results
        with open(engine.scratchpad_path, 'r') as f:
            results = f.read()

        # Should contain multiple Prime programs
        assert 'PRMG/Prime Connect' in results
        assert 'PRMG/Plus Connect' in results  # Other programs should be included

    @pytest.mark.requires_db
    def test_query_with_multiple_selected_programs(self, test_db_path, monkeypatch):
        """
        Test that query returns data for multiple selected programs.
        """
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = query_engine.QueryEngine(db_path=test_db_path, use_llm=False)
        parser = ContextAwareParser(db_path=test_db_path)

        # Select multiple programs
        selected_programs = ["PRMG/Prime Connect", "PRMG/Plus Connect"]

        parameters = {
            'param_name': 'citizenship',
            'loan_servicer': 'Prime',
            'selected_programs': selected_programs
        }

        success = parser.execute_script('find_param_across_programs', parameters)

        assert success is True

        # Read results
        with open(engine.scratchpad_path, 'r') as f:
            results = f.read()

        # Both programs should be in results
        assert 'PRMG/Prime Connect' in results
        assert 'PRMG/Plus Connect' in results

        # Verify filtering message shows correct count
        assert 'Filtered by Selected Programs: 2' in results or 'Selected Programs' in results


    @pytest.mark.requires_db
    def test_empty_selected_programs_returns_all(self, test_db_path, monkeypatch):
        """
        Test that empty selected_programs list returns all programs for servicer.
        """
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        engine = query_engine.QueryEngine(db_path=test_db_path, use_llm=False)
        parser = ContextAwareParser(db_path=test_db_path)

        # Empty list should behave like no context
        parameters = {
            'param_name': 'citizenship',
            'loan_servicer': 'Prime',
            'selected_programs': []  # Empty list
        }

        success = parser.execute_script('find_param_across_programs', parameters)

        assert success is True

        # Read results
        with open(engine.scratchpad_path, 'r') as f:
            results = f.read()

        # Should return all Prime programs when list is empty
        assert 'PRMG/Prime Connect' in results
        assert 'PRMG/Plus Connect' in results
