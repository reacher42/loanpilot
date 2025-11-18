#!/usr/bin/env python3
"""
Context-aware query parser using Anthropic with structured tool interfaces.
Provides formal script interfaces and context to Anthropic for accurate routing.
"""

import sqlite3
import os
import json
import logging
from typing import Dict, List, Optional, Any
from anthropic import Anthropic
from .adaptive_model_selector import create_adaptive_selector

logger = logging.getLogger(__name__)


class ContextAwareParser:
    """
    Enhanced parser that provides structured context and script interfaces to Anthropic.
    Uses tool/function calling pattern for accurate parameter extraction.
    """

    def __init__(self, db_path='loanpilot.db'):
        self.db_path = os.environ.get('DB_PATH', db_path)
        self.scratchpad_path = os.environ.get('SCRATCHPAD_PATH', '.scratchpad')

        # Initialize Anthropic client with adaptive model selection
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            print("⚠️  ANTHROPIC_API_KEY not found - context-aware parsing will fail")
            self.anthropic = None
            self.model_selector = None
        else:
            self.anthropic = Anthropic(api_key=api_key)
            # Use 'balanced' tier for context-aware parsing (needs good reasoning)
            self.model_selector = create_adaptive_selector(self.anthropic, tier='balanced')

        # Load database schema and scripts
        self.db_columns = self._get_database_columns()
        self.script_tools = self._build_script_tools()

        print(f"✓ Context-aware parser initialized")
        print(f"  - {len(self.db_columns)} database columns")
        print(f"  - {len(self.script_tools)} script tools")

    def _get_database_columns(self) -> List[str]:
        """Get list of all columns in programs_v3 table."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(programs_v3)")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return columns

    def _build_script_tools(self) -> List[Dict[str, Any]]:
        """
        Build structured tool definitions for each script.
        These will be passed to Anthropic for function calling.
        """
        tools = [
            {
                "name": "find_param_across_programs",
                "description": "Query a specific parameter across multiple programs. Use when user asks about a parameter (citizenship, appraisal, reserves, etc.) with selected programs.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "param_name": {
                            "type": "string",
                            "description": f"Database column name. Available: {', '.join(self.db_columns)}",
                            "enum": self.db_columns
                        },
                        "loan_servicer": {
                            "type": "string",
                            "description": "Loan servicer name (Prime or LoanStream)",
                            "enum": ["Prime", "LoanStream"]
                        },
                        "selected_programs": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of selected program names to query"
                        }
                    },
                    "required": ["param_name", "loan_servicer"]
                }
            },
            {
                "name": "show_program_parameters",
                "description": "Show all parameters for a specific program. Use when user asks about all parameters for ONE program.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "program_name": {
                            "type": "string",
                            "description": "Full program name (e.g., 'PRMG/Prime Connect')"
                        },
                        "loan_servicer": {
                            "type": "string",
                            "description": "Loan servicer (Prime or LoanStream)",
                            "enum": ["Prime", "LoanStream"]
                        }
                    },
                    "required": ["program_name", "loan_servicer"]
                }
            },
            {
                "name": "match_programs",
                "description": "Find matching programs based on borrower profile (credit score, loan amount, LTV, DTI, etc.)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "borrower_credit_score": {"type": "string"},
                        "loan_amount": {"type": "string"},
                        "ltv": {"type": "string"},
                        "dti": {"type": "string"},
                        "transaction_type": {"type": "string"},
                        "occupancy": {"type": "string"}
                    },
                    "required": []
                }
            }
        ]
        return tools

    def _map_param_name(self, user_param: str) -> Optional[str]:
        """
        Map user's natural language parameter name to database column.
        Uses fuzzy matching and common aliases.
        """
        user_param_lower = user_param.lower().replace(' ', '_')

        # Direct match
        if user_param_lower in self.db_columns:
            return user_param_lower

        # Common aliases
        aliases = {
            'citizenship': 'citizenship',
            'appraisal': 'appraisal_requirements',
            'appraisals': 'appraisal_requirements',
            'reserves': 'reserves',
            'reserve': 'reserves',
            'documentation': 'income_documentation',
            'docs': 'income_documentation',
            'occupancy': 'occupancy',
            'transaction': 'transaction_type',
            'credit': 'borrower_credit_score',
            'ltv': 'ltv',
            'dti': 'dti',
            'loan_amount': 'loan_amount'
        }

        if user_param_lower in aliases:
            return aliases[user_param_lower]

        # Fuzzy match
        import difflib
        matches = difflib.get_close_matches(user_param_lower, self.db_columns, n=1, cutoff=0.6)
        if matches:
            return matches[0]

        return None

    def parse_query_with_context(
        self,
        query: str,
        selected_programs: List[str] = None,
        selected_servicers: List[str] = None
    ) -> Dict[str, Any]:
        """
        Parse query using Anthropic with full context awareness.

        Args:
            query: User's natural language query
            selected_programs: List of selected program names
            selected_servicers: List of selected servicers

        Returns:
            Dict with script_name, parameters, and confidence
        """
        # Build context message
        context_parts = []
        if selected_programs:
            context_parts.append(f"Selected programs: {', '.join(selected_programs)}")
        if selected_servicers:
            context_parts.append(f"Servicers: {', '.join(selected_servicers)}")

        context_message = "\n".join(context_parts) if context_parts else "No programs selected"

        # Build system prompt
        system_prompt = f"""You are an expert at routing loan program queries to the correct database script.

Database Schema - Available parameter columns:
{', '.join(self.db_columns)}

User Context:
{context_message}

Your task:
1. Understand what the user is asking about
2. Map natural language to the correct database column name
3. Choose the appropriate script tool with correct parameters
4. If programs are selected, use them in selected_programs parameter

Common parameter mappings:
- "appraisal requirements" → appraisal_requirements
- "citizenship requirements" → citizenship
- "reserve requirements" → reserves
- "documentation requirements" → income_documentation
- "occupancy requirements" → occupancy
"""

        # Check if Anthropic client is available
        if not self.anthropic or not self.model_selector:
            return {
                "script_name": None,
                "parameters": {},
                "confidence": 0.0,
                "error": "Anthropic API not available (missing API key)"
            }

        # Call Anthropic with tool use and adaptive model selection
        try:
            response, model_used = self.model_selector.call_with_fallback(
                max_tokens=1024,
                temperature=0,
                system=system_prompt,
                messages=[{
                    "role": "user",
                    "content": f"Query: {query}"
                }],
                tools=self.script_tools
            )
            logger.info(f"Context-aware parsing used model: {model_used}")

            # Extract tool use from response
            for block in response.content:
                if block.type == "tool_use":
                    tool_name = block.name
                    tool_input = block.input

                    print(f"✓ Anthropic selected tool: {tool_name}")
                    print(f"✓ Tool parameters: {json.dumps(tool_input, indent=2)}")

                    # Add selected_programs if provided and not in tool_input
                    if selected_programs and 'selected_programs' not in tool_input:
                        tool_input['selected_programs'] = selected_programs

                    # Infer servicer from selected programs if not provided
                    if 'loan_servicer' in tool_input and not tool_input.get('loan_servicer'):
                        if selected_servicers:
                            tool_input['loan_servicer'] = selected_servicers[0]
                        elif selected_programs and selected_programs[0].startswith('PRMG/'):
                            tool_input['loan_servicer'] = 'Prime'

                    return {
                        "script_name": tool_name,
                        "parameters": tool_input,
                        "confidence": 0.95,
                        "reasoning": getattr(block, 'reasoning', None)
                    }

            # No tool use found
            return {
                "script_name": None,
                "parameters": {},
                "confidence": 0.0,
                "error": "No matching script found"
            }

        except Exception as e:
            print(f"❌ Anthropic query parsing failed: {e}")
            return {
                "script_name": None,
                "parameters": {},
                "confidence": 0.0,
                "error": str(e)
            }

    def execute_script(self, script_name: str, parameters: Dict[str, Any]) -> bool:
        """
        Execute the selected script with parameters.
        Loads script from database and executes with proper context.
        """
        # Load script from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT script FROM scripts WHERE name = ?", (script_name,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            with open(self.scratchpad_path, 'w') as f:
                f.write(f"Error: Script '{script_name}' not found in database\n")
            return False

        script_code = row[0]

        # Prepare execution context
        exec_globals = {
            'db_path': self.db_path,
            'scratchpad_path': self.scratchpad_path,
            '__name__': '__main__',
            **parameters  # Add all parameters to globals
        }

        # Execute script
        try:
            exec(script_code, exec_globals)
            return True
        except SystemExit:
            # Scripts may call exit() - treat as success
            return True
        except Exception as e:
            with open(self.scratchpad_path, 'w') as f:
                f.write(f"Error executing script: {str(e)}\n")
            return False

    def parse_and_execute(
        self,
        query: str,
        selected_programs: List[str] = None,
        selected_servicers: List[str] = None
    ) -> bool:
        """
        Full pipeline: parse query with context and execute matched script.
        """
        # Remove ^ prefix if present
        if query.startswith('^'):
            query = query[1:].strip()

        # Parse query
        result = self.parse_query_with_context(
            query,
            selected_programs=selected_programs,
            selected_servicers=selected_servicers
        )

        if not result['script_name']:
            error_msg = result.get('error', 'No matching script found')
            with open(self.scratchpad_path, 'w') as f:
                f.write(f"Error: {error_msg}\n")
            return False

        # Execute script
        return self.execute_script(result['script_name'], result['parameters'])


def main():
    """Test the context-aware parser."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python src/context_aware_parser.py <query>")
        print("Example: python src/context_aware_parser.py 'What are the citizenship requirements'")
        sys.exit(1)

    query = ' '.join(sys.argv[1:])

    # Simulate selected programs from environment
    import json
    context_json = os.getenv('QUERY_CONTEXT', '{}')
    context = json.loads(context_json) if context_json else {}

    parser = ContextAwareParser()
    success = parser.parse_and_execute(
        query,
        selected_programs=context.get('selected_programs'),
        selected_servicers=context.get('selected_servicers')
    )

    if success:
        scratchpad_path = os.environ.get('SCRATCHPAD_PATH', '.scratchpad')
        try:
            with open(scratchpad_path, 'r') as f:
                print("\nResults:")
                print("=" * 80)
                print(f.read())
                print("=" * 80)
        except FileNotFoundError:
            print("\nNo results generated.")
    else:
        print("\nExecution failed.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
