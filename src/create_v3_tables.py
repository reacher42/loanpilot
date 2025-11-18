#!/usr/bin/env python3
"""
Create v3 database tables from the transposed TSV structure.
In v3, attributes are rows and programs are columns (opposite of v2).
"""

import sqlite3
import csv
import sys
from pathlib import Path

# Database path
DB_PATH = Path(__file__).parent.parent / "loanpilot.db"
TSV_PATH = Path(__file__).parent.parent / "data" / "v3" / "Non-QM_Matrix.xlsx - Attributes.tsv"

def create_v3_schema(conn):
    """Create v3 tables with transposed structure"""
    cursor = conn.cursor()

    # Drop existing v3 tables if they exist
    cursor.execute("DROP TABLE IF EXISTS programs_v3")
    cursor.execute("DROP TABLE IF EXISTS prime_v3")
    cursor.execute("DROP TABLE IF EXISTS loanstream_v3")

    # Create programs_v3 - unified table with all programs
    cursor.execute("""
        CREATE TABLE programs_v3 (
            attribute_group TEXT,
            attribute_name TEXT,
            "values" TEXT,
            borrower_facing TEXT,
            prmg_prime_connect_verbatim TEXT,
            prmg_prime_connect TEXT,
            prmg_plus_connect TEXT,
            prmg_flex_connect_prime TEXT,
            prmg_flex_connect_plus TEXT,
            prmg_elite_connect_prime TEXT,
            prmg_alternative_aus TEXT,
            prmg_choice_stretched TEXT,
            prmg_choice_non_prime TEXT,
            notes TEXT,
            for_discussion TEXT,
            alternate_name TEXT,
            attribute_generic_name TEXT,
            description TEXT,
            uom TEXT,
            loanstream_select_nonqm TEXT,
            loanstream_core_nonqm TEXT,
            loanstream_select_dscr TEXT,
            loanstream_core_dscr TEXT,
            loanstream_sub1_dscr TEXT,
            loanstream_no_ratio_dscr TEXT,
            loanstream_dscr_5_8_unit TEXT,
            format_status TEXT
        )
    """)

    # Create prime_v3 - PRMG programs only
    cursor.execute("""
        CREATE TABLE prime_v3 (
            attribute_group TEXT,
            attribute_name TEXT,
            "values" TEXT,
            borrower_facing TEXT,
            prmg_prime_connect_verbatim TEXT,
            prmg_prime_connect TEXT,
            prmg_plus_connect TEXT,
            prmg_flex_connect_prime TEXT,
            prmg_flex_connect_plus TEXT,
            prmg_elite_connect_prime TEXT,
            prmg_alternative_aus TEXT,
            prmg_choice_stretched TEXT,
            prmg_choice_non_prime TEXT,
            notes TEXT,
            for_discussion TEXT,
            alternate_name TEXT,
            attribute_generic_name TEXT,
            description TEXT,
            uom TEXT
        )
    """)

    # Create loanstream_v3 - LoanStream programs only
    cursor.execute("""
        CREATE TABLE loanstream_v3 (
            attribute_group TEXT,
            attribute_name TEXT,
            "values" TEXT,
            borrower_facing TEXT,
            loanstream_select_nonqm TEXT,
            loanstream_core_nonqm TEXT,
            loanstream_select_dscr TEXT,
            loanstream_core_dscr TEXT,
            loanstream_sub1_dscr TEXT,
            loanstream_no_ratio_dscr TEXT,
            loanstream_dscr_5_8_unit TEXT,
            notes TEXT,
            for_discussion TEXT,
            alternate_name TEXT,
            attribute_generic_name TEXT,
            description TEXT,
            uom TEXT,
            format_status TEXT
        )
    """)

    conn.commit()
    print("✓ Created v3 table schemas")

def populate_v3_tables(conn):
    """Read TSV file and populate v3 tables"""
    cursor = conn.cursor()

    if not TSV_PATH.exists():
        print(f"✗ TSV file not found: {TSV_PATH}")
        return False

    with open(TSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='\t')
        header = next(reader)  # Skip header row

        row_count = 0
        for row in reader:
            # Ensure row has enough columns (pad with empty strings if needed)
            while len(row) < 28:
                row.append('')

            # Extract columns
            attribute_group = row[0].strip()
            attribute_name = row[1].strip()
            values = row[2].strip()
            borrower_facing = row[3].strip()

            # PRMG programs (columns 4-12)
            prmg_prime_connect_verbatim = row[4].strip()
            prmg_prime_connect = row[5].strip()
            prmg_plus_connect = row[6].strip()
            prmg_flex_connect_prime = row[7].strip()
            prmg_flex_connect_plus = row[8].strip()
            prmg_elite_connect_prime = row[9].strip()
            prmg_alternative_aus = row[10].strip()
            prmg_choice_stretched = row[11].strip()
            prmg_choice_non_prime = row[12].strip()

            # Documentation (columns 13-18)
            notes = row[13].strip()
            for_discussion = row[14].strip()
            alternate_name = row[15].strip()
            attribute_generic_name = row[16].strip()
            description = row[17].strip()
            uom = row[18].strip()

            # LoanStream programs (columns 19-25)
            loanstream_select_nonqm = row[19].strip()
            loanstream_core_nonqm = row[20].strip()
            # Column 21 is blank
            loanstream_select_dscr = row[22].strip()
            loanstream_core_dscr = row[23].strip()
            loanstream_sub1_dscr = row[24].strip()
            loanstream_no_ratio_dscr = row[25].strip()
            loanstream_dscr_5_8_unit = row[26].strip()

            # Format status (column 27)
            format_status = row[27].strip() if len(row) > 27 else ''

            # Insert into programs_v3 (unified table)
            cursor.execute("""
                INSERT INTO programs_v3 (
                    attribute_group, attribute_name, "values", borrower_facing,
                    prmg_prime_connect_verbatim, prmg_prime_connect, prmg_plus_connect,
                    prmg_flex_connect_prime, prmg_flex_connect_plus, prmg_elite_connect_prime,
                    prmg_alternative_aus, prmg_choice_stretched, prmg_choice_non_prime,
                    notes, for_discussion, alternate_name, attribute_generic_name,
                    description, uom,
                    loanstream_select_nonqm, loanstream_core_nonqm,
                    loanstream_select_dscr, loanstream_core_dscr, loanstream_sub1_dscr,
                    loanstream_no_ratio_dscr, loanstream_dscr_5_8_unit,
                    format_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attribute_group, attribute_name, values, borrower_facing,
                prmg_prime_connect_verbatim, prmg_prime_connect, prmg_plus_connect,
                prmg_flex_connect_prime, prmg_flex_connect_plus, prmg_elite_connect_prime,
                prmg_alternative_aus, prmg_choice_stretched, prmg_choice_non_prime,
                notes, for_discussion, alternate_name, attribute_generic_name,
                description, uom,
                loanstream_select_nonqm, loanstream_core_nonqm,
                loanstream_select_dscr, loanstream_core_dscr, loanstream_sub1_dscr,
                loanstream_no_ratio_dscr, loanstream_dscr_5_8_unit,
                format_status
            ))

            # Insert into prime_v3 (PRMG only)
            cursor.execute("""
                INSERT INTO prime_v3 (
                    attribute_group, attribute_name, "values", borrower_facing,
                    prmg_prime_connect_verbatim, prmg_prime_connect, prmg_plus_connect,
                    prmg_flex_connect_prime, prmg_flex_connect_plus, prmg_elite_connect_prime,
                    prmg_alternative_aus, prmg_choice_stretched, prmg_choice_non_prime,
                    notes, for_discussion, alternate_name, attribute_generic_name,
                    description, uom
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attribute_group, attribute_name, values, borrower_facing,
                prmg_prime_connect_verbatim, prmg_prime_connect, prmg_plus_connect,
                prmg_flex_connect_prime, prmg_flex_connect_plus, prmg_elite_connect_prime,
                prmg_alternative_aus, prmg_choice_stretched, prmg_choice_non_prime,
                notes, for_discussion, alternate_name, attribute_generic_name,
                description, uom
            ))

            # Insert into loanstream_v3 (LoanStream only)
            cursor.execute("""
                INSERT INTO loanstream_v3 (
                    attribute_group, attribute_name, "values", borrower_facing,
                    loanstream_select_nonqm, loanstream_core_nonqm,
                    loanstream_select_dscr, loanstream_core_dscr, loanstream_sub1_dscr,
                    loanstream_no_ratio_dscr, loanstream_dscr_5_8_unit,
                    notes, for_discussion, alternate_name, attribute_generic_name,
                    description, uom, format_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                attribute_group, attribute_name, values, borrower_facing,
                loanstream_select_nonqm, loanstream_core_nonqm,
                loanstream_select_dscr, loanstream_core_dscr, loanstream_sub1_dscr,
                loanstream_no_ratio_dscr, loanstream_dscr_5_8_unit,
                notes, for_discussion, alternate_name, attribute_generic_name,
                description, uom, format_status
            ))

            row_count += 1

        conn.commit()
        print(f"✓ Populated v3 tables with {row_count} attributes")
        return True

def verify_v3_tables(conn):
    """Verify that v3 tables were created and populated correctly"""
    cursor = conn.cursor()

    print("\n=== V3 Tables Verification ===")

    for table_name in ['programs_v3', 'prime_v3', 'loanstream_v3']:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"{table_name}: {count} rows")

        # Show sample row
        cursor.execute(f"SELECT attribute_name, attribute_group FROM {table_name} LIMIT 1")
        sample = cursor.fetchone()
        if sample:
            print(f"  Sample: {sample[0]} ({sample[1]})")

    # Show some specific attributes
    print("\n=== Sample Attribute Values ===")
    cursor.execute("""
        SELECT attribute_name, prmg_prime_connect, loanstream_select_nonqm
        FROM programs_v3
        WHERE attribute_name IN ('borrower_credit_score', 'loan_amount', 'ltv', 'dti')
    """)
    for row in cursor.fetchall():
        print(f"{row[0]}: PRMG={row[1][:50]}... | LoanStream={row[2][:50]}...")

def main():
    """Main execution"""
    print("Creating v3 database tables...")
    print(f"Database: {DB_PATH}")
    print(f"TSV file: {TSV_PATH}")

    try:
        conn = sqlite3.connect(DB_PATH)

        # Create schema
        create_v3_schema(conn)

        # Populate tables
        if populate_v3_tables(conn):
            verify_v3_tables(conn)
            print("\n✓ V3 tables created successfully!")
        else:
            print("\n✗ Failed to populate v3 tables")
            return 1

        conn.close()
        return 0

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
