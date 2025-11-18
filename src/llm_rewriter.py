#!/usr/bin/env python3
"""
LLM-based query rewriter using Anthropic Claude for natural language understanding.
Converts user queries into structured commands that match available scripts.
Uses RAG (Retrieval-Augmented Generation) to map user queries to database parameters.
"""

import os
import time
import json
import sqlite3
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class LLMRewriter:
    """Rewrites natural language queries using Anthropic Claude with RAG for parameter matching."""

    def __init__(self, model_name: str = "claude-3-5-haiku-20241022", cache_size: int = 1000,
                 embedding_model: str = "sentence-transformers/all-mpnet-base-v2"):
        """
        Initialize the LLM rewriter with parameter RAG.

        Args:
            model_name: Anthropic model name (default: claude-3-5-haiku for speed/cost)
            cache_size: Maximum number of cached query rewrites
            embedding_model: Sentence transformer model for parameter retrieval
        """
        self.model_name = model_name
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.client = None
        self.cache: Dict[str, tuple] = {}  # {query: (rewritten, timestamp)}
        self.cache_size = cache_size
        self.cache_ttl = timedelta(hours=1)
        self.anthropic_available = False
        self.load_error = None

        # Parameter RAG components
        self.embedding_model_name = embedding_model
        self.embedding_model = None
        self.param_embeddings = None
        self.param_metadata = None
        self.rag_available = False

        # Initialize Anthropic client and RAG
        self._init_client()
        self._init_parameter_rag()

    def _init_client(self) -> bool:
        """
        Initialize Anthropic client.

        Returns:
            True if client initialized successfully, False otherwise
        """
        if self.anthropic_available:
            return True

        if self.load_error:
            return False

        if not self.api_key:
            self.load_error = "ANTHROPIC_API_KEY not found in environment"
            print(f"⚠ {self.load_error}")
            print("Will fall back to semantic matching only")
            return False

        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
            self.anthropic_available = True
            print(f"✓ Anthropic API initialized")
            print(f"✓ Using model: {self.model_name}")
            return True
        except Exception as e:
            self.load_error = str(e)
            print(f"⚠ Could not initialize Anthropic client: {e}")
            print("Will fall back to semantic matching only")
            return False

    def _init_parameter_rag(self) -> bool:
        """
        Initialize parameter RAG system with embeddings.

        Returns:
            True if RAG initialized successfully, False otherwise
        """
        if self.rag_available:
            return True

        try:
            # Import sentence transformers
            from sentence_transformers import SentenceTransformer, util
            import torch

            # Load embedding model
            self.embedding_model = SentenceTransformer(self.embedding_model_name)

            # Load parameter metadata from database
            db_path = os.environ.get('DB_PATH', 'loanpilot.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT column_name, attribute_group, display_name, possible_values,
                       borrower_facing, common_terms, description
                FROM parameter_metadata
                ORDER BY column_name
            ''')

            self.param_metadata = []
            param_texts = []

            for row in cursor.fetchall():
                column_name, attribute_group, display_name, possible_values, borrower_facing, common_terms_json, description = row
                common_terms = json.loads(common_terms_json)

                # Create rich text for embedding: combine all information
                param_text_parts = [
                    f"{display_name}.",
                    f"{description}" if description else "",
                    f"Category: {attribute_group}." if attribute_group else "",
                    f"Possible values: {possible_values}." if possible_values else "",
                    f"Common terms: {', '.join(common_terms)}.",
                    f"Column: {column_name}"
                ]
                param_text = " ".join([p for p in param_text_parts if p])
                param_texts.append(param_text)

                self.param_metadata.append({
                    'column_name': column_name,
                    'attribute_group': attribute_group,
                    'display_name': display_name,
                    'possible_values': possible_values,
                    'borrower_facing': borrower_facing,
                    'common_terms': common_terms,
                    'description': description
                })

            conn.close()

            if not param_texts:
                print("⚠ No parameters found in parameter_metadata table")
                return False

            # Generate embeddings for all parameters
            self.param_embeddings = self.embedding_model.encode(param_texts, convert_to_tensor=True)
            self.rag_available = True

            print(f"✓ Parameter RAG initialized with {len(self.param_metadata)} parameters")
            return True

        except Exception as e:
            print(f"⚠ Could not initialize parameter RAG: {e}")
            print("Will fall back to manual parameter mappings")
            return False

    def retrieve_relevant_parameters(self, query: str, top_k: int = 8) -> List[Dict]:
        """
        Retrieve most relevant parameters for a user query using semantic search.

        Args:
            query: User's natural language query
            top_k: Number of top parameters to retrieve

        Returns:
            List of parameter metadata dictionaries
        """
        if not self.rag_available or self.embedding_model is None or self.param_embeddings is None:
            return []

        try:
            from sentence_transformers import util

            # Embed the query
            query_embedding = self.embedding_model.encode(query, convert_to_tensor=True)

            # Calculate cosine similarities
            similarities = util.cos_sim(query_embedding, self.param_embeddings)[0]

            # Get top-k indices
            k = min(top_k, len(self.param_metadata))
            top_results = similarities.topk(k=k)

            # Return parameter metadata sorted by relevance
            relevant_params = []
            for idx, score in zip(top_results.indices.tolist(), top_results.values.tolist()):
                param = self.param_metadata[idx].copy()
                param['relevance_score'] = float(score)
                relevant_params.append(param)

            return relevant_params

        except Exception as e:
            import traceback
            print(f"⚠ Error retrieving parameters: {e}")
            print(traceback.format_exc())
            return []

    def _check_cache(self, query: str) -> Optional[str]:
        """
        Check if query result is in cache and still valid.

        Args:
            query: User's query

        Returns:
            Cached rewritten query or None
        """
        if query in self.cache:
            rewritten, timestamp = self.cache[query]
            if datetime.now() - timestamp < self.cache_ttl:
                return rewritten
            else:
                # Expired, remove from cache
                del self.cache[query]
        return None

    def _update_cache(self, query: str, rewritten: str):
        """
        Update cache with new rewrite result.

        Args:
            query: Original query
            rewritten: Rewritten query
        """
        # Implement simple LRU: if cache full, remove oldest entry
        if len(self.cache) >= self.cache_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        self.cache[query] = (rewritten, datetime.now())

    def _build_prompt(self, query: str, available_scripts: List[str],
                      relevant_params: Optional[List[Dict]] = None) -> str:
        """
        Build prompt for Claude to rewrite query with RAG-retrieved parameters.

        Args:
            query: User's natural language query
            available_scripts: List of available script prompts
            relevant_params: RAG-retrieved relevant parameters (optional)

        Returns:
            Formatted prompt for Claude
        """
        scripts_list = "\n".join([f"- {s}" for s in available_scripts])

        # Build parameter mappings section using RAG if available
        if relevant_params is not None and len(relevant_params) > 0:
            param_mappings = []
            for param in relevant_params:
                # Create mapping line with common terms and category
                terms = ', '.join([f'"{term}"' for term in param['common_terms'][:3]])  # Top 3 terms
                category_info = f" ({param['attribute_group']})" if param.get('attribute_group') else ""
                param_mappings.append(f"  * {terms}{category_info} → {param['column_name']}")

            param_section = "- Map these common terms to the correct database column names:\n" + "\n".join(param_mappings)
        else:
            # Fallback to manual mappings if RAG not available
            param_section = """- Map common terms to database column names:
  * "appraisal transfer" → "appraisal_transfer_allowed"
  * "appraisal review" → "appraisal_review_required"
  * "credit score" → "borrower_credit_score"
  * "loan amount" → "loan_amount"
  * "DTI", "debt to income" → "dti"
  * "LTV", "loan to value" → "ltv"""

        prompt = f"""You are a query rewriter for a loan program database system.

Your task: Rewrite the user's natural language query to match ONE of the available script patterns below. Output ONLY the rewritten query with no explanation.

Available script patterns:
{scripts_list}

Guidelines:
- Identify the user's intent (find parameter, show programs, match borrowers, etc.)
- Extract key entities: parameter names, program names, servicer names
- Match to the most appropriate script pattern
- CRITICAL: Parameter name must come IMMEDIATELY after "Find" - use format "Find {{param_name}} across programs"
- When user asks "What are the X" or "What is the X" where X looks like a parameter name, rewrite to "Find X across programs"
- Use exact database column names (with underscores)
{param_section}

Examples:
User query: "What is the loan amount range allowed"
Rewritten: Find loan_amount across programs

User query: "What is the max dti limit?"
Rewritten: Find dti across programs

User query: "What are the conditions for allowing appraisal transfer?"
Rewritten: Find appraisal_transfer_allowed across programs

User query: "Tell me about credit score requirements across all programs"
Rewritten: Find borrower_credit_score across programs

User query: "Can you show me what PRMG/Prime Connect supports"
Rewritten: Find all parameters for PRMG/Prime Connect

Now rewrite this query:
User query: {query}
Rewritten:"""

        return prompt

    def rewrite_query(self, query: str, available_scripts: List[str]) -> Optional[str]:
        """
        Rewrite a natural language query into a structured command using Claude with RAG.

        Args:
            query: User's natural language query
            available_scripts: List of available script prompts for context

        Returns:
            Rewritten query or None if rewriting failed
        """
        # Check cache first
        cached = self._check_cache(query)
        if cached:
            print(f"💾 Using cached rewrite: '{query}' → '{cached}'")
            return cached

        # Check Anthropic availability
        if not self._init_client():
            return None  # Fall back to semantic matching

        try:
            # Retrieve relevant parameters using RAG
            relevant_params = None
            if self.rag_available:
                relevant_params = self.retrieve_relevant_parameters(query, top_k=8)
                if relevant_params and len(relevant_params) > 0:
                    param_names = ', '.join([p['column_name'] for p in relevant_params[:3]])
                    print(f"🔍 Retrieved {len(relevant_params)} relevant parameters: {param_names}...")

            # Build prompt with RAG-retrieved parameters
            prompt = self._build_prompt(query, available_scripts, relevant_params)

            # Call Anthropic API
            start_time = time.time()
            message = self.client.messages.create(
                model=self.model_name,
                max_tokens=100,  # Short response expected
                temperature=0.3,  # Low temperature for consistency
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            elapsed = time.time() - start_time

            # Extract response
            if not message.content or len(message.content) == 0:
                print("⚠ Claude returned empty response")
                return None

            rewritten = message.content[0].text.strip()

            if not rewritten:
                print("⚠ Could not extract query from Claude response")
                return None

            # Clean up response - remove quotes if present
            rewritten = rewritten.strip('"\'')

            print(f"🤖 Claude rewrite ({elapsed:.2f}s): '{query}' → '{rewritten}'")

            # Update cache
            self._update_cache(query, rewritten)

            return rewritten

        except Exception as e:
            print(f"⚠ Error during Claude query rewriting: {e}")
            return None  # Fall back to semantic matching

    def get_available_scripts_list(self) -> List[str]:
        """
        Get list of available script prompts from database.
        This is a helper method to fetch script prompts for prompt building.

        Returns:
            List of script prompt strings
        """
        import sqlite3

        try:
            db_path = os.environ.get('DB_PATH', 'loanpilot.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT prompt FROM scripts ORDER BY name")
            scripts = [row[0] for row in cursor.fetchall()]
            conn.close()
            return scripts
        except Exception as e:
            print(f"⚠ Error fetching scripts: {e}")
            return [
                "Find parameter value across programs",
                "Find all parameters for a given program",
                "Get parameter value for a program",
                "Match programs for borrower criteria",
                "Show all parameters supported by program",
                "Show programs for loan servicer"
            ]
