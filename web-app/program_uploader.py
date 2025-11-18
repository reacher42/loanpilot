#!/usr/bin/env python3
"""
Program Uploader - Handle TSV file uploads for new loan programs.
Validates, transforms, and imports single-program TSV files into the database.
"""

import sqlite3
import pandas as pd
import io
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of TSV validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    program_name: Optional[str] = None
    servicer: Optional[str] = None
    row_count: int = 0
    attributes_matched: int = 0


class ProgramUploader:
    """Handle TSV file upload, validation, and database import for new programs"""

    EXPECTED_ROW_COUNT = 60
    REQUIRED_METADATA_COLUMNS = [
        "Attribute Group",
        "Attribute Name",
        "Values",
        "Borrower Facing"
    ]

    def __init__(self, db_path: str = "loanpilot.db"):
        self.db_path = Path(db_path)

    def detect_servicer(self, program_name: str) -> Tuple[str, str]:
        """
        Detect servicer from program name.
        Returns: (servicer, table_name)

        Examples:
            "PRMG/New Program" -> ("Prime", "prime_v3")
            "LoanStream-New DSCR" -> ("LoanStream", "loanstream_v3")
        """
        if program_name.startswith("PRMG/") or program_name.startswith("Prime/"):
            return "Prime", "prime_v3"
        elif program_name.startswith("LoanStream-") or program_name.startswith("LoanStream/"):
            return "LoanStream", "loanstream_v3"
        else:
            # Default to Prime if ambiguous
            return "Prime", "prime_v3"

    def get_existing_attributes(self, table_name: str) -> List[str]:
        """Get list of existing attribute names from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(f'SELECT "Attribute Name" FROM {table_name} ORDER BY rowid')
        attributes = [row[0] for row in cursor.fetchall()]

        conn.close()
        return attributes

    def normalize_tsv_content(self, content: bytes) -> str:
        """Normalize line endings in TSV content"""
        # Remove embedded CRs within fields
        content = content.replace(b'\r\n', b'\n')  # CRLF -> LF
        content = content.replace(b'\r', b'')      # Remove remaining CRs
        return content.decode('utf-8')

    def validate_tsv(self, file_content: bytes, filename: str) -> ValidationResult:
        """
        Validate uploaded TSV file structure and content.

        Checks:
        - File format (TSV)
        - Row count (must be 60)
        - Metadata columns match existing
        - Exactly one new program column
        - Attribute names match existing database
        """
        errors = []
        warnings = []

        # Normalize and parse TSV
        try:
            normalized_content = self.normalize_tsv_content(file_content)
            df = pd.read_csv(io.StringIO(normalized_content), sep='\t', engine='python')
        except Exception as e:
            errors.append(f"Failed to parse TSV file: {str(e)}")
            return ValidationResult(False, errors, warnings)

        # Check row count
        row_count = len(df)
        if row_count != self.EXPECTED_ROW_COUNT:
            errors.append(f"Expected {self.EXPECTED_ROW_COUNT} rows, got {row_count}")

        # Check metadata columns
        for col in self.REQUIRED_METADATA_COLUMNS:
            if col not in df.columns:
                errors.append(f"Missing required metadata column: '{col}'")

        if errors:
            return ValidationResult(False, errors, warnings, row_count=row_count)

        # Find program columns (exclude metadata and documentation columns)
        metadata_cols = set(self.REQUIRED_METADATA_COLUMNS)
        doc_cols = {'Notes', 'For discussion (variable not consistent with definition)',
                   'Alternate Name', 'Attribute Generic Name', 'Description', 'uom',
                   'format status'}

        program_cols = [col for col in df.columns
                       if col not in metadata_cols and col not in doc_cols and col.strip()]

        if len(program_cols) == 0:
            errors.append("No program column found in TSV file")
            return ValidationResult(False, errors, warnings, row_count=row_count)

        if len(program_cols) > 1:
            errors.append(f"Expected 1 program column, found {len(program_cols)}: {', '.join(program_cols)}")
            return ValidationResult(False, errors, warnings, row_count=row_count)

        program_name = program_cols[0]
        servicer, table_name = self.detect_servicer(program_name)

        # Validate attribute names match existing database
        existing_attributes = self.get_existing_attributes(table_name)
        tsv_attributes = df["Attribute Name"].tolist()

        matches = sum(1 for i, attr in enumerate(tsv_attributes)
                     if i < len(existing_attributes) and attr == existing_attributes[i])

        if matches < len(existing_attributes) * 0.9:  # 90% match threshold
            warnings.append(f"Only {matches}/{len(existing_attributes)} attributes matched existing database")

        # Check for empty values
        empty_count = df[program_name].isna().sum() + (df[program_name] == '').sum()
        if empty_count > 0:
            warnings.append(f"{empty_count} empty values found in program column")

        # Success
        return ValidationResult(
            is_valid=True,
            errors=[],
            warnings=warnings,
            program_name=program_name,
            servicer=servicer,
            row_count=row_count,
            attributes_matched=matches
        )

    def column_name_to_sql(self, column_name: str) -> str:
        """Convert program name to valid SQL column name"""
        # Replace special characters with underscores
        sql_name = re.sub(r'[^a-zA-Z0-9_]', '_', column_name)
        # Remove consecutive underscores
        sql_name = re.sub(r'_+', '_', sql_name)
        # Remove leading/trailing underscores
        sql_name = sql_name.strip('_')
        return sql_name

    def import_program(self, file_content: bytes, program_name: str, servicer: str) -> Dict:
        """
        Import validated TSV file into the database.
        Adds new program column to appropriate table (prime_v3 or loanstream_v3).

        Returns: Dictionary with import status and details
        """
        table_name = "prime_v3" if servicer == "Prime" else "loanstream_v3"

        try:
            # Parse TSV
            normalized_content = self.normalize_tsv_content(file_content)
            df = pd.read_csv(io.StringIO(normalized_content), sep='\t', engine='python')

            # Extract program data
            program_data = df[program_name].tolist()

            # Connect to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if column already exists
            cursor.execute(f'PRAGMA table_info({table_name})')
            existing_cols = [col[1] for col in cursor.fetchall()]

            if program_name in existing_cols:
                conn.close()
                return {
                    "success": False,
                    "error": f"Program '{program_name}' already exists in {table_name}"
                }

            # Add new column
            sql_col_name = f'"{program_name}"'  # Quote to handle special characters
            cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {sql_col_name} TEXT')

            # Update each row with program data
            for idx, value in enumerate(program_data, start=1):
                cursor.execute(
                    f'UPDATE {table_name} SET {sql_col_name} = ? WHERE rowid = ?',
                    (str(value) if pd.notna(value) else '', idx)
                )

            conn.commit()

            # Verify import
            cursor.execute(f'SELECT COUNT(*) FROM {table_name} WHERE {sql_col_name} IS NOT NULL')
            updated_count = cursor.fetchone()[0]

            conn.close()

            return {
                "success": True,
                "program_name": program_name,
                "servicer": servicer,
                "table_name": table_name,
                "rows_updated": updated_count,
                "message": f"Successfully imported program '{program_name}' into {table_name}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Import failed: {str(e)}"
            }

    def get_servicers(self) -> List[Dict[str, str]]:
        """Get list of available servicers"""
        return [
            {"name": "Prime", "table": "prime_v3", "prefix": "PRMG/"},
            {"name": "LoanStream", "table": "loanstream_v3", "prefix": "LoanStream-"}
        ]

    def get_program_count(self, servicer: str) -> int:
        """Get count of programs for a servicer"""
        table_name = "prime_v3" if servicer == "Prime" else "loanstream_v3"

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Count columns (subtract 4 metadata columns)
        cursor.execute(f'PRAGMA table_info({table_name})')
        col_count = len(cursor.fetchall())

        conn.close()

        return col_count - 4  # Exclude metadata columns
