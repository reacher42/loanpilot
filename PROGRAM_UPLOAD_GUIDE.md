# Program Upload Feature - User Guide

## Overview

The Program Upload feature allows you to add new loan programs to the LoanPilot system by uploading a TSV (Tab-Separated Values) file directly through the web interface.

## Quick Start

1. **Click "Upload Program"** button in the header
2. **Select your TSV file** (must contain exactly 1 program with 60 attributes)
3. **Review validation results** (errors, warnings, program info)
4. **Click "Import Program"** if validation passed
5. **Wait for confirmation** and page reload

## TSV File Requirements

### File Structure

Your TSV file must have **exactly 5 columns**:

| Column 1 | Column 2 | Column 3 | Column 4 | Column 5 |
|----------|----------|----------|----------|----------|
| Attribute Group | Attribute Name | Values | Borrower Facing | **[Your Program Name]** |

### Requirements Checklist

- ✅ **61 rows total** (1 header + 60 data rows)
- ✅ **5 columns** (4 metadata + 1 program column)
- ✅ **Tab-separated format** (.tsv or .txt file)
- ✅ **Metadata columns** must match existing database structure
- ✅ **Program name** must start with:
  - `PRMG/` or `Prime/` for Prime servicer programs
  - `LoanStream-` or `LoanStream/` for LoanStream programs
- ✅ **60 attributes** matching the exact order in the database

### Example Header Row

```
Attribute Group	Attribute Name	Values	Borrower Facing	PRMG/My New Program
```

### Attribute Names (Must Match Exactly)

The TSV must include these 60 attributes in this order:

1. program_summary
2. channel
3. income
4. borrower_credit_score
5. co-borrower_credit_score
6. qualifying_credit_score
7. dti
8. cash_out
9. loan_amount
10. loan_type
11. occupancy
12. property_type
13. reserves
14. 30day_mortgage_lates_in_06_months
15. 30day_mortgage_lates_in_12_months
16. 30day_mortgage_lates_in_24_months
17. 60day_mortgage_lates_in_12_months
18. 60day_mortgage_lates_in_24_months
19. 90day_mortgage_lates_in_24_months
20. 120day_mortgage_lates_in_12_months

... (and 40 more - see database for full list)

## How to Create a TSV File

### Option 1: Export from Excel

1. Open the master program matrix in Excel
2. Select the 4 metadata columns + your new program column
3. **File → Save As → Tab Delimited Text (.txt)**
4. Rename to `.tsv` extension

### Option 2: Copy from Existing Program

```bash
# Extract a sample program column from existing data
head -61 "data/v3/Non-QM_Matrix.xlsx - Attributes.tsv" | \
  cut -f1-4,6 > my_new_program.tsv

# Edit the header to rename the program
# Edit column 5 values to reflect your new program criteria
```

### Option 3: Create from Template

Use the test file generator:

```python
import csv

# Create template with all 60 attributes
attributes = [
    "program_summary", "channel", "income",
    "borrower_credit_score", # ... etc
]

with open('template.tsv', 'w', newline='') as f:
    writer = csv.writer(f, delimiter='\t')

    # Header row
    writer.writerow([
        "Attribute Group",
        "Attribute Name",
        "Values",
        "Borrower Facing",
        "PRMG/My New Program"
    ])

    # Data rows (fill in with your program criteria)
    for attr in attributes:
        writer.writerow([
            "",  # Attribute Group
            attr,  # Attribute Name
            "",  # Values
            "",  # Borrower Facing
            ""   # Your program value
        ])
```

## Validation Process

When you upload a file, the system automatically validates:

### ✅ What is Checked

1. **File Format**: Valid TSV structure
2. **Row Count**: Exactly 60 data rows (+ 1 header)
3. **Column Count**: 5 columns (4 metadata + 1 program)
4. **Metadata Columns**: Match existing database
5. **Attribute Names**: Match 90%+ of existing attributes
6. **Program Name**: Valid servicer prefix
7. **Servicer Detection**: Auto-detects Prime vs LoanStream

### ⚠️ Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Expected 60 rows, got X" | Wrong number of rows | Check your data has exactly 60 attributes |
| "Missing required metadata column" | Missing Attribute Name, etc. | Include all 4 metadata columns |
| "No program column found" | Only metadata columns | Add your program column as column 5 |
| "Expected 1 program column, found X" | Multiple program columns | Keep only 1 program column |

### ℹ️ Warnings (Non-Blocking)

- **"X empty values found"**: Some attributes have no value (allowed)
- **"Only X/60 attributes matched"**: Attribute names don't match perfectly

## Import Process

After successful validation:

1. **Review Program Info**:
   - Program Name: `PRMG/My New Program`
   - Servicer: `Prime`
   - Rows: `60`
   - Attributes Matched: `60/60`

2. **Click "Import Program"**:
   - New column added to `prime_v3` or `loanstream_v3` table
   - All 60 attribute values populated
   - Database updated atomically

3. **Confirmation**:
   - Success message with row count
   - Auto-reload after 2 seconds
   - New program immediately available for queries

## After Import

### Verify Program Added

```sql
-- Check program exists
SELECT "PRMG/My New Program"
FROM prime_v3
WHERE "Attribute Name" = 'program_summary';
```

### Query New Program

The new program is immediately available:

```
Query: "show programs for Prime"
Result: [Your new program appears in the list]

Query: "find all parameters for PRMG/My New Program"
Result: [All 60 attributes displayed]
```

## Troubleshooting

### Problem: "Validation failed" with errors

**Solution**: Check the error messages in the alert box:
- Fix row count (must be 60 + header)
- Fix column count (must be 5 total)
- Match attribute names exactly

### Problem: "Import failed: Program already exists"

**Solution**: The program name is already in the database:
- Rename your program in the header row
- Or delete the existing program first

### Problem: Empty values warning

**Solution**: This is normal! Many programs don't have values for all attributes.
- Proceed with import if validation passed
- Empty values will be stored as empty strings

### Problem: File won't upload

**Solution**:
- Check file extension is `.tsv` or `.txt`
- Verify file is tab-separated (not comma or space)
- Check file size (should be small, < 100KB)

## Technical Details

### API Endpoints

```
GET  /api/programs/servicers  - List servicers (Prime, LoanStream)
POST /api/programs/validate   - Validate TSV file
POST /api/programs/import     - Import validated TSV
GET  /api/programs/count      - Get program counts
```

### Database Changes

When you import a program:

```sql
-- New column added to table
ALTER TABLE prime_v3 ADD COLUMN "PRMG/My New Program" TEXT;

-- Values populated for all 60 rows
UPDATE prime_v3
SET "PRMG/My New Program" = ?
WHERE rowid = ?;
```

### File Processing Flow

```
User selects file
    ↓
Frontend → POST /api/programs/validate
    ↓
Backend validates structure (60 rows, 5 cols)
    ↓
Backend checks attribute matching
    ↓
Frontend displays results
    ↓
User clicks Import
    ↓
Frontend → POST /api/programs/import
    ↓
Backend adds column to prime_v3 or loanstream_v3
    ↓
Backend populates 60 rows
    ↓
Success! Page reloads
```

## Sample TSV File

Located at: `/tmp/test_new_program.tsv`

```tsv
Attribute Group	Attribute Name	Values	Borrower Facing	PRMG/Test New Program
Program/Product	program_summary			Near prime solutions...
Channel	channel	Retail, Wholesale...		Retail, Wholesale...
Income	income	2 years + YTD...	yes	2 years + YTD...
Credit	borrower_credit_score	300 to 850	maybe	>=660
... (56 more rows)
```

## Best Practices

1. **Test First**: Use a test program name like `PRMG/Test XYZ` first
2. **Backup Database**: Always backup before importing production programs
3. **Validate Carefully**: Review all warnings before importing
4. **Match Attributes**: Copy attribute values from similar programs
5. **Clear Naming**: Use descriptive program names (e.g., `PRMG/Elite Prime Plus`)
6. **Document Changes**: Keep notes on when/why programs were added

## Related Documentation

- [README.md](README.md) - Main project overview
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Architecture details
- [loanpilot_aws_deployment.md](loanpilot_aws_deployment.md) - Deployment guide

## Support

For issues or questions:
1. Check validation error messages
2. Review this guide
3. Check logs: `web-app/logs/loanpilot.log`
4. Test with sample TSV file first
