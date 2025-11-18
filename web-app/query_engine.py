"""
Query execution engine for FastAPI.
Direct integration with Python parser - no subprocess spawning.
"""

import sys
import os
import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from io import StringIO
from contextlib import redirect_stdout, redirect_stderr

# Add parent directory to path to import src modules
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.context_aware_parser import ContextAwareParser as QueryParser
except ImportError:
    try:
        from src.parser_anthropic import QueryParser
    except ImportError:
        from src.parser import QueryParser

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    FastAPI integration layer for query parsing and execution.
    Replaces subprocess spawning with direct function calls.
    """

    def __init__(self, db_path: str = None, use_llm: bool = True):
        """
        Initialize the query engine.

        Args:
            db_path: Path to SQLite database (defaults to loanpilot.db in project root)
            use_llm: Whether to use LLM for query rewriting (default: True)
        """
        # Determine project root
        self.project_root = Path(__file__).parent.parent
        self.db_path = db_path or str(self.project_root / "loanpilot.db")

        # Set scratchpad path to project root before parser initialization
        self.scratchpad_path = str(self.project_root / ".scratchpad_web")
        os.environ['SCRATCHPAD_PATH'] = self.scratchpad_path

        # Verify database exists
        if not Path(self.db_path).exists():
            logger.error(f"Database not found at {self.db_path}")
            raise FileNotFoundError(f"Database not found: {self.db_path}")

        # Initialize parser with direct integration
        logger.info(f"Initializing QueryParser with db_path={self.db_path}")
        try:
            # Try new context-aware parser first (no use_llm param)
            self.parser = QueryParser(db_path=self.db_path)
            logger.info("✓ Using ContextAwareParser with Anthropic tool calling")
        except TypeError:
            # Fallback to old parser with use_llm param
            self.parser = QueryParser(db_path=self.db_path, use_llm=use_llm)
            logger.info("✓ Using legacy QueryParser")

        logger.info("✓ Query engine initialized successfully")

    def execute_query(self, query: str, context_params: Dict = None) -> Dict:
        """
        Execute a query with context parameters.

        Args:
            query: User's natural language query
            context_params: Dictionary with selected_programs, selected_servicers, etc.

        Returns:
            Dictionary with success, query, results, stdout, executedAt
        """
        # Normalize query (add ^ prefix if missing)
        normalized_query = query.strip()
        if not normalized_query.startswith('^'):
            normalized_query = f"^ {normalized_query}"

        context_params = context_params or {}

        logger.info(f"🔍 Executing query: {normalized_query}")
        if context_params:
            logger.info(f"📌 Context params: {context_params}")

        # Set context in environment (for scripts that read it)
        os.environ['QUERY_CONTEXT'] = json.dumps(context_params)
        os.environ['DB_PATH'] = self.db_path

        # Use in-memory scratchpad instead of file
        scratchpad = StringIO()

        # Capture stdout/stderr
        stdout_capture = StringIO()
        stderr_capture = StringIO()

        try:
            # Execute with captured output
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Check if parser supports context (new context-aware parser)
                if hasattr(self.parser, 'parse_and_execute') and \
                   'selected_programs' in context_params or 'selected_servicers' in context_params:
                    # New context-aware parser
                    success = self.parser.parse_and_execute(
                        normalized_query.replace('^', '').strip(),
                        selected_programs=context_params.get('selected_programs'),
                        selected_servicers=context_params.get('selected_servicers')
                    )
                else:
                    # Fallback to old parser
                    success = self.parser.parse_and_execute(normalized_query.replace('^', '').strip())

            # Read results from scratchpad file
            results = ""
            if Path(self.scratchpad_path).exists():
                with open(self.scratchpad_path, 'r') as f:
                    results = f.read().strip()

            stdout_text = stdout_capture.getvalue().strip()
            stderr_text = stderr_capture.getvalue().strip()

            if success:
                logger.info(f"✅ Query executed successfully")
                return {
                    "success": True,
                    "query": normalized_query,
                    "results": results,
                    "stdout": stdout_text if stdout_text else None,
                    "executedAt": datetime.utcnow().isoformat()
                }
            else:
                logger.error(f"❌ Query execution failed: {results}")
                return {
                    "success": False,
                    "query": normalized_query,
                    "results": results or "Query execution failed",
                    "stdout": stdout_text if stdout_text else None,
                    "executedAt": datetime.utcnow().isoformat()
                }

        except Exception as e:
            logger.error(f"❌ Exception during query execution: {e}", exc_info=True)
            return {
                "success": False,
                "query": normalized_query,
                "results": f"Error executing query: {str(e)}",
                "stdout": stdout_capture.getvalue().strip() if stdout_capture else None,
                "executedAt": datetime.utcnow().isoformat()
            }
        finally:
            # Clean up environment
            os.environ.pop('QUERY_CONTEXT', None)

    def get_available_scripts(self) -> List[Dict]:
        """
        Get list of available scripts from database.

        Returns:
            List of dicts with name, description, prompt
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            cursor = conn.cursor()

            cursor.execute("""
                SELECT name, description, prompt
                FROM scripts
                ORDER BY name
            """)

            scripts = [dict(row) for row in cursor.fetchall()]
            conn.close()

            logger.info(f"✓ Found {len(scripts)} available scripts")
            return scripts

        except Exception as e:
            logger.error(f"❌ Error fetching scripts: {e}")
            raise

    def check_health(self) -> Dict:
        """
        Check health of query engine and dependencies.

        Returns:
            Dict with available status and configuration
        """
        try:
            # Check if database is accessible
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM scripts")
            script_count = cursor.fetchone()[0]
            conn.close()

            # Check if parser is initialized
            available = self.parser is not None and script_count > 0

            return {
                "available": available,
                "pythonPath": sys.executable,
                "parserScript": str(Path(__file__).parent.parent / "src" / "parser.py"),
                "dbPath": self.db_path,
                "scriptCount": script_count,
                "error": None
            }

        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {
                "available": False,
                "pythonPath": sys.executable,
                "parserScript": None,
                "dbPath": self.db_path,
                "error": str(e)
            }

    def fetch_program_details(self, programs: List[str], servicer: str) -> Dict[str, Dict]:
        """
        Fetch program details from database.

        Args:
            programs: List of program names
            servicer: Loan servicer (Prime or LoanStream)

        Returns:
            Dict mapping program names to their details
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            details = {}
            for program in programs:
                cursor.execute("""
                    SELECT program_summary, borrower_credit_score, loan_amount, ltv, dti
                    FROM programs_v3
                    WHERE loan_servicer = ? AND program_name = ?
                """, (servicer, program))

                row = cursor.fetchone()
                if row:
                    details[program] = dict(row)

            conn.close()
            logger.info(f"✓ Fetched details for {len(details)}/{len(programs)} programs")
            return details

        except Exception as e:
            logger.error(f"❌ Error fetching program details: {e}")
            return {}

    def fetch_program_parameter(self, program_name: str, servicer: str, param_name: str) -> Optional[str]:
        """
        Fetch a specific parameter value for a program.

        Args:
            program_name: Program name
            servicer: Loan servicer
            param_name: Parameter name to fetch

        Returns:
            Parameter value or None
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(f"""
                SELECT {param_name}
                FROM programs_v3
                WHERE loan_servicer = ? AND program_name = ?
            """, (servicer, program_name))

            row = cursor.fetchone()
            conn.close()

            if row and row[0]:
                return row[0]
            return None

        except Exception as e:
            logger.error(f"❌ Error fetching parameter {param_name}: {e}")
            return None


# Singleton instance
_query_engine: Optional[QueryEngine] = None


def get_query_engine() -> QueryEngine:
    """
    Get singleton instance of QueryEngine.
    Lazy initialization on first call.
    """
    global _query_engine
    if _query_engine is None:
        _query_engine = QueryEngine()
    return _query_engine
