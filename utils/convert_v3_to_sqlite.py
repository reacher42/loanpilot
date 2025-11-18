#!/usr/bin/env python3
"""
Convert v3 TSV file to SQLite database.
Creates prime_v3 and loanstream_v3 tables from data/v3/Non-QM_Matrix.xlsx - Attributes.tsv
Structure: rows = attributes, columns = metadata + programs (same as v2)
"""

import sqlite3
import pandas as pd
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_database(db_path='loanpilot.db'):
    """Create or connect to SQLite database."""
    logger.info(f"Connecting to database: {db_path}")
    conn = sqlite3.connect(db_path)
    return conn


def convert_v3_to_tables(tsv_path, conn):
    """
    Convert v3 TSV file to prime_v3 and loanstream_v3 tables.

    Columns structure:
    - 0-3: Metadata (Attribute Group, Attribute Name, Values, Borrower Facing)
    - 4-12: PRMG programs (9 programs)
    - 13-18: Documentation columns (Notes, etc.)
    - 19-26: LoanStream programs (7 programs)
    """
    logger.info(f"Reading v3 data from {tsv_path.name}")

    try:
        # Read file (has mixed CRLF, CR line endings and embedded CR within fields)
        with open(tsv_path, 'rb') as f:
            binary_content = f.read()

        # Remove embedded CRs within fields (they appear as \r followed by non-newline)
        # Keep only CRs that are part of line endings
        binary_content = binary_content.replace(b'\r\n', b'\n')  # CRLF -> LF
        binary_content = binary_content.replace(b'\r', b'')       # Remove remaining CRs

        # Decode to string
        content = binary_content.decode('utf-8')

        # Parse the normalized content
        from io import StringIO
        df = pd.read_csv(StringIO(content), sep='\t', engine='python', on_bad_lines='warn')

        logger.info(f"  Total rows: {len(df)}, Total columns: {len(df.columns)}")
        logger.info(f"  All columns: {list(df.columns)}")

        # Define column groups
        metadata_cols = df.columns[0:4].tolist()
        prmg_cols = df.columns[4:13].tolist()
        loanstream_cols = [col for col in df.columns if 'LoanStream' in col]

        logger.info(f"  Metadata columns: {metadata_cols}")
        logger.info(f"  PRMG columns ({len(prmg_cols)}): {prmg_cols}")
        logger.info(f"  LoanStream columns ({len(loanstream_cols)}): {loanstream_cols}")

        # Create prime_v3 table (metadata + PRMG programs)
        prime_v3_cols = metadata_cols + prmg_cols
        df_prime = df[prime_v3_cols].copy()

        logger.info(f"\nCreating prime_v3 table with {len(prime_v3_cols)} columns")
        df_prime.to_sql('prime_v3', conn, if_exists='replace', index=False)

        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM prime_v3")
        count = cursor.fetchone()[0]
        logger.info(f"✓ Created prime_v3 with {count} rows")

        # Create loanstream_v3 table (metadata + LoanStream programs)
        loanstream_v3_cols = metadata_cols + loanstream_cols
        df_loanstream = df[loanstream_v3_cols].copy()

        logger.info(f"\nCreating loanstream_v3 table with {len(loanstream_v3_cols)} columns")
        df_loanstream.to_sql('loanstream_v3', conn, if_exists='replace', index=False)

        cursor.execute("SELECT COUNT(*) FROM loanstream_v3")
        count = cursor.fetchone()[0]
        logger.info(f"✓ Created loanstream_v3 with {count} rows")

        return True

    except Exception as e:
        logger.error(f"✗ Error converting v3 data: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main conversion process for v3 files."""
    logger.info("=" * 60)
    logger.info("Starting v3 TSV to SQLite conversion")
    logger.info("=" * 60)

    # Define paths
    v3_tsv = Path('data/v3/Non-QM_Matrix.xlsx - Attributes.tsv')
    db_path = 'loanpilot.db'

    # Check if file exists
    if not v3_tsv.exists():
        logger.error(f"v3 TSV file not found at {v3_tsv}")
        return

    # Create database connection
    conn = create_database(db_path)

    # Show existing tables
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    existing_tables = [row[0] for row in cursor.fetchall()]
    logger.info(f"Existing tables before conversion: {existing_tables}")

    # Convert v3 data
    if convert_v3_to_tables(v3_tsv, conn):
        # Commit and show results
        conn.commit()

        # Show final table list
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        all_tables = [row[0] for row in cursor.fetchall()]

        logger.info("\n" + "=" * 60)
        logger.info("Conversion complete!")
        logger.info(f"Database updated: {db_path}")
        logger.info(f"All tables: {all_tables}")

        # Show sample data
        logger.info("\n" + "=" * 60)
        logger.info("Sample data from prime_v3 (first 3 rows):")
        logger.info("=" * 60)
        sample_df = pd.read_sql_query("SELECT * FROM prime_v3 LIMIT 3", conn)
        for idx, row in sample_df.iterrows():
            logger.info(f"\nRow {idx + 1}:")
            logger.info(f"  Attribute: {row['Attribute Name']}")
            logger.info(f"  Group: {row['Attribute Group']}")
            # Show first PRMG program value
            first_program_col = sample_df.columns[4]
            logger.info(f"  {first_program_col}: {str(row[first_program_col])[:80]}...")

        logger.info("\n" + "=" * 60)
        logger.info("Sample data from loanstream_v3 (first 3 rows):")
        logger.info("=" * 60)
        sample_df = pd.read_sql_query("SELECT * FROM loanstream_v3 LIMIT 3", conn)
        for idx, row in sample_df.iterrows():
            logger.info(f"\nRow {idx + 1}:")
            logger.info(f"  Attribute: {row['Attribute Name']}")
            logger.info(f"  Group: {row['Attribute Group']}")
            # Show first LoanStream program value
            first_program_col = [col for col in sample_df.columns if 'LoanStream' in col][0]
            logger.info(f"  {first_program_col}: {str(row[first_program_col])[:80]}...")

        logger.info("\n" + "=" * 60)
    else:
        logger.error("Conversion failed")

    conn.close()


if __name__ == "__main__":
    main()
