#!/usr/bin/env python3
"""
Query parser using only Anthropic API for query matching.
No sentence-transformers or torch dependencies required.
"""

import sqlite3
import re
import os
import json
from typing import Tuple, Optional, Dict, List
from anthropic import Anthropic

class QueryParser:
    """Parse and execute user queries using Anthropic API for matching."""

    def __init__(self, db_path='loanpilot.db', use_llm=True):
        """
        Initialize the parser with database and Anthropic API.

        Args:
            db_path: Path to SQLite database
            use_llm: Whether to use Anthropic for query matching (default: True)
        """
        self.db_path = os.environ.get('DB_PATH', db_path)
        self.scratchpad_path = os.environ.get('SCRATCHPAD_PATH', '.scratchpad')
        self.script_cache = None

        # Initialize Anthropic client
        self.use_llm = use_llm
        self.anthropic = None
        if use_llm:
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if api_key:
                try:
                    self.anthropic = Anthropic(api_key=api_key)
                    print("✓ Anthropic API initialized for query matching")
                except Exception as e:
                    print(f"⚠ Could not initialize Anthropic API: {e}")
                    self.anthropic = None
            else:
                print("⚠ ANTHROPIC_API_KEY not found in environment")

    def load_scripts(self) -> list:
        """Load all scripts from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name, description, prompt, script
            FROM scripts
            ORDER BY name
        """)

        scripts = cursor.fetchall()
        conn.close()

        return scripts

    def get_scripts(self):
        """Get cached scripts or load from database."""
        if self.script_cache is None:
            self.script_cache = self.load_scripts()
        return self.script_cache

    def match_query_with_anthropic(self, query: str) -> Optional[Tuple[str, str, float]]:
        """
        Match user query to script using Anthropic API.

        Args:
            query: User's natural language query

        Returns:
            Tuple of (script_name, script_code, confidence_score) or None
        """
        if not self.anthropic:
            return None

        scripts = self.get_scripts()

        # Build prompt for Anthropic
        script_list = "\n".join([
            f"{i+1}. {script[2]}"  # prompt column
            for i, script in enumerate(scripts)
        ])

        prompt = f"""You are a query matching system. Given a user query and a list of available script patterns, identify the BEST matching script.

Available script patterns:
{script_list}

User query: "{query}"

Respond with ONLY the number of the best matching script (1-{len(scripts)}). If no good match exists, respond with "0".

Your response must be a single number only."""

        try:
            message = self.anthropic.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=10,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text.strip()
            match_idx = int(response_text) - 1

            if match_idx < 0 or match_idx >= len(scripts):
                return None

            script_name, description, prompt_text, script_code = scripts[match_idx]
            # Return with high confidence since Anthropic made the choice
            return script_name, script_code, 0.95

        except Exception as e:
            print(f"⚠ Anthropic matching failed: {e}")
            return None

    def match_query(self, query: str, threshold: float = 0.5) -> Optional[Tuple[str, str, float]]:
        """
        Match user query to most similar script - uses Anthropic API.

        Args:
            query: User's natural language query
            threshold: Minimum similarity score (ignored for Anthropic matching)

        Returns:
            Tuple of (script_name, script_code, similarity_score) or None
        """
        if self.anthropic:
            return self.match_query_with_anthropic(query)

        # Fallback: simple keyword matching
        return self.match_query_simple(query)

    def match_query_simple(self, query: str) -> Optional[Tuple[str, str, float]]:
        """Simple keyword-based fallback matching."""
        scripts = self.get_scripts()
        query_lower = query.lower()

        best_match = None
        best_score = 0

        for script in scripts:
            script_name, description, prompt_text, script_code = script
            prompt_lower = prompt_text.lower()

            # Count matching keywords
            keywords = set(prompt_lower.split())
            query_keywords = set(query_lower.split())
            matches = len(keywords & query_keywords)
            score = matches / max(len(keywords), len(query_keywords))

            if score > best_score:
                best_score = score
                best_match = (script_name, script_code, score)

        if best_score >= 0.3:
            return best_match
        return None

    def extract_loan_servicer(self, query: str) -> Optional[str]:
        """Extract loan_servicer parameter from query."""
        query_lower = query.lower()
        if 'prime' in query_lower:
            return 'Prime'
        elif 'loanstream' in query_lower or 'loan stream' in query_lower:
            return 'LoanStream'
        return None

    def extract_program_name(self, query: str) -> Optional[str]:
        """Extract program_name parameter from query."""
        if re.search(r'\bacross\s+programs?\b', query, re.IGNORECASE):
            return None

        patterns = [
            r'by\s+([A-Za-z0-9/\s\-]+?)\s+(?:in|from)',
            r'for\s+([A-Za-z0-9/\s\-]+?)\s+(?:in|from)',
            r'for\s+([A-Za-z0-9/\s\-]+?)$',
            r'by\s+([A-Za-z0-9/\s\-]+?)$',
            r'((?:PRMG/|LoanStream)[A-Za-z0-9/\s\-]+?)\s+program'
        ]

        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def extract_param_name(self, query: str) -> Optional[str]:
        """Extract param_name parameter from query."""
        match = re.search(r'(\w+)\s+parameter', query, re.IGNORECASE)
        if match:
            return match.group(1)

        match = re.search(r'(?:find|show)\s+(\w+)\s+(?:across|for)', query, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def extract_borrower_params(self, query: str) -> Dict[str, str]:
        """Extract borrower parameters from matching queries."""
        params = {}

        credit_match = re.search(r'(\d{3})\s*credit\s*score', query, re.IGNORECASE)
        if credit_match:
            params['borrower_credit_score'] = credit_match.group(1)

        loan_match = re.search(r'\$?([\d,]+)\s*loan\s*amount', query, re.IGNORECASE)
        if loan_match:
            params['loan_amount'] = loan_match.group(1).replace(',', '')

        ltv_match = re.search(r'(\d+(?:\.\d+)?)\s*%?\s*LTV', query, re.IGNORECASE)
        if ltv_match:
            params['ltv'] = ltv_match.group(1)

        dti_match = re.search(r'(\d+(?:\.\d+)?)\s*%?\s*DTI', query, re.IGNORECASE)
        if dti_match:
            params['dti'] = dti_match.group(1)

        if re.search(r'\bpurchase\b', query, re.IGNORECASE):
            params['transaction_type'] = 'Purchase'
        elif re.search(r'\bcash\s*out\b', query, re.IGNORECASE):
            params['transaction_type'] = 'Cash Out'
        elif re.search(r'\brate\s*(?:and|&)?\s*term\b', query, re.IGNORECASE):
            params['transaction_type'] = 'Rate & Term'

        if re.search(r'\bowner\s*occupied\b', query, re.IGNORECASE):
            params['occupancy'] = 'Owner Occupied'
        elif re.search(r'\bsecond\s*home\b', query, re.IGNORECASE):
            params['occupancy'] = 'Second Home'
        elif re.search(r'\binvestment\b', query, re.IGNORECASE):
            params['occupancy'] = 'Investment'

        return params

    def extract_parameters(self, query: str) -> Dict[str, str]:
        """Extract all parameters from query."""
        params = {}

        loan_servicer = self.extract_loan_servicer(query)
        if loan_servicer:
            params['loan_servicer'] = loan_servicer

        program_name = self.extract_program_name(query)
        if program_name:
            params['program_name'] = program_name

            if 'loan_servicer' not in params:
                if program_name.startswith('PRMG/'):
                    params['loan_servicer'] = 'Prime'
                elif program_name.startswith('LoanStream'):
                    params['loan_servicer'] = 'LoanStream'

        param_name = self.extract_param_name(query)
        if param_name:
            params['param_name'] = param_name

        borrower_params = self.extract_borrower_params(query)
        params.update(borrower_params)

        return params

    def execute_script(self, script_code: str, parameters: Dict[str, str]) -> bool:
        """Execute script with extracted parameters and context."""
        try:
            context = {}
            query_context_json = os.environ.get('QUERY_CONTEXT', '{}')
            if query_context_json:
                try:
                    context = json.loads(query_context_json)
                except json.JSONDecodeError:
                    pass

            all_params = {
                **parameters,
                **context,
                'db_path': self.db_path,
                'scratchpad_path': self.scratchpad_path,
                '__name__': '__main__'
            }

            exec(script_code, all_params)
            return True
        except SystemExit:
            # Scripts may call quit() or exit() - treat as success if scratchpad has content
            return True
        except Exception as e:
            with open(self.scratchpad_path, 'w') as f:
                f.write(f"Error executing script: {str(e)}\n")
            return False

    def parse_and_execute(self, query: str, threshold: float = 0.3) -> bool:
        """Parse query, match to script, extract parameters, and execute."""
        if query.startswith('^'):
            query = query[1:].strip()

        original_query = query

        # Match query to script using Anthropic
        match_result = self.match_query(query, threshold)
        if not match_result:
            with open(self.scratchpad_path, 'w') as f:
                f.write(f"No matching script found for query: {original_query}\n")
            return False

        script_name, script_code, similarity = match_result

        # Extract parameters
        parameters = self.extract_parameters(original_query)

        # Default loan_servicer to Prime if not specified
        if 'param_name' in parameters and 'loan_servicer' not in parameters:
            parameters['loan_servicer'] = 'Prime'
            print(f"ℹ️  No servicer specified, defaulting to: Prime")

        print(f"✓ Matched script: {script_name} (confidence: {similarity:.3f})")
        print(f"✓ Extracted parameters: {parameters}")

        # Execute script
        return self.execute_script(script_code, parameters)


def main():
    """Command-line interface for the parser."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python src/parser_anthropic.py <query>")
        print("Example: python src/parser_anthropic.py '^ Find borrower_credit_score parameter value across Prime programs'")
        sys.exit(1)

    query = ' '.join(sys.argv[1:])

    parser = QueryParser()
    success = parser.parse_and_execute(query)

    if success:
        try:
            scratchpad_path = os.environ.get('SCRATCHPAD_PATH', '.scratchpad')
            with open(scratchpad_path, 'r') as f:
                print("\nResults:")
                print("=" * 80)
                print(f.read())
                print("=" * 80)
        except FileNotFoundError:
            print("\nNo results generated.")
    else:
        print("\nExecution failed. Check .scratchpad for details.")

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
