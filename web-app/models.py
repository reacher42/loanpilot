"""
Pydantic models for FastAPI request/response validation.
Ensures type safety and automatic API documentation.
"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


class ProgramSelection(BaseModel):
    """Represents a selected loan program for context."""
    program_name: str = Field(..., alias="programName", description="Name of the loan program")
    servicer: str = Field(..., description="Loan servicer (Prime or LoanStream)")

    class Config:
        populate_by_name = True


class QueryRequest(BaseModel):
    """Request model for query execution."""
    query: str = Field(..., min_length=1, max_length=500, description="Query string (with or without ^ prefix)")
    selected_programs: Optional[str] = Field(None, alias="selectedPrograms", description="JSON string of selected programs")
    program_context: Optional[str] = Field(None, alias="programContext", description="Human-readable program context")

    class Config:
        populate_by_name = True

    @field_validator('query')
    @classmethod
    def validate_query(cls, v: str) -> str:
        """Ensure query is not empty after stripping."""
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


class QueryResponse(BaseModel):
    """Response model for query execution."""
    success: bool = Field(..., description="Whether the query executed successfully")
    query: str = Field(..., description="The executed query")
    results: str = Field(..., description="Query results from scratchpad")
    stdout: Optional[str] = Field(None, description="Python stdout if any")
    executed_at: str = Field(..., alias="executedAt", description="ISO timestamp of execution")

    class Config:
        populate_by_name = True


class ParsedQueryResponse(BaseModel):
    """Parsed and formatted query response for HTMX."""
    header: str = Field(..., description="Results panel header")
    summary: str = Field(..., description="Brief summary for chat bubble")
    structured_data: str = Field(..., alias="structuredData", description="HTML formatted results")
    auto_select_program: Optional[Dict[str, str]] = Field(None, alias="autoSelectProgram", description="Program to auto-select if any")

    class Config:
        populate_by_name = True


class ScriptInfo(BaseModel):
    """Information about an available script."""
    name: str = Field(..., description="Unique script identifier")
    description: str = Field(..., description="Human-readable description")
    prompt: str = Field(..., description="Natural language pattern to match")


class ScriptsResponse(BaseModel):
    """Response model for available scripts."""
    success: bool = Field(..., description="Whether the request succeeded")
    scripts: List[ScriptInfo] = Field(..., description="List of available scripts")


class HealthResponse(BaseModel):
    """Response model for health check."""
    success: bool = Field(..., description="Whether the service is healthy")
    available: bool = Field(..., description="Whether Python bridge is available")
    python_path: Optional[str] = Field(None, alias="pythonPath", description="Path to Python executable")
    parser_script: Optional[str] = Field(None, alias="parserScript", description="Path to parser script")
    db_path: Optional[str] = Field(None, alias="dbPath", description="Path to database")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: str = Field(..., description="ISO timestamp of health check")

    class Config:
        populate_by_name = True


class ProgramDetails(BaseModel):
    """Details about a loan program from database."""
    program_summary: Optional[str] = Field(None, alias="programSummary")
    borrower_credit_score: Optional[str] = Field(None, alias="borrowerCreditScore")
    loan_amount: Optional[str] = Field(None, alias="loanAmount")
    ltv: Optional[str] = None
    dti: Optional[str] = None

    class Config:
        populate_by_name = True


class ErrorResponse(BaseModel):
    """Standard error response."""
    success: bool = Field(default=False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
