# LoanPilot

AI-powered loan program matching system with natural language query support and interactive electron app interface.

## Overview

LoanPilot is a comprehensive system for managing, querying, and matching loan programs from multiple servicers (Prime/PRMG and LoanStream). It provides:

- **SQLite Database**: Structured storage of loan program attributes and criteria
- **Natural Language Query Parser**: Semantic search using sentence-transformers for intuitive queries
- **Script Management**: Store and execute Python scripts without creating files
- **Electron Desktop App**: Interactive UI with program selection and context-aware queries
- **Program Matching Engine**: Match borrower profiles to eligible loan programs

## Quick Start

### 🐳 Docker Deployment (Recommended)

**Deploy in 3 commands:**

```bash
git clone https://github.com/reacher42/loanpilot.git
cd loanpilot
cp .env.example .env  # Add your ANTHROPIC_API_KEY
docker-compose up -d
```

Access: **http://localhost:8000**

📚 **Full Guide**: [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md)

### 🔧 Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Setup database (first time only)
python utils/convert_v3_to_sqlite.py && python utils/transpose_v3_tables.py
python utils/init_scripts_table.py

# Start application
cd electron-loan-app
npm install
npm start
```

## Project Structure

```
loanpilot/
├── data/v3/                         # Current production data
│   └── Non-QM_Matrix.xlsx - Attributes.tsv
├── docs/                            # Design & analysis documentation
│   ├── design.md
│   ├── parameter_analysis.md
│   ├── parameter_refactoring_guide.md
│   └── ba_parameter_guide.md
├── src/
│   ├── parser.py                    # Sentence-transformers query parser (production)
│   └── parser_qwen.py               # Qwen1.5-0.5B alternative parser
├── utils/
│   ├── convert_v3_to_sqlite.py      # TSV → SQLite conversion
│   ├── transpose_v3_tables.py       # Create programs_v3 table
│   ├── init_scripts_table.py        # Initialize scripts database
│   ├── manage_scripts.py            # Manage stored scripts
│   └── run_script.py                # Execute stored scripts
├── electron-loan-app/               # Desktop application
│   ├── src/
│   │   ├── index.html               # Main UI with program selection
│   │   └── server/
│   │       ├── engines/python-bridge.js
│   │       └── routes/query.js
│   ├── main.js
│   └── TESTING_GUIDE.md
├── loanpilot.db                     # SQLite database
├── .scratchpad                      # Query execution output
└── README.md                        # This file
```

## Core Features

### 1. Database Management

#### Database Tables

| Table | Rows | Columns | Description |
|-------|------|---------|-------------|
| `programs_v3` | 16 | 62 | **Production**: Programs as rows, attributes as columns |
| `prime_v3` | 60 | 13 | Prime programs (attributes as rows, intermediate) |
| `loanstream_v3` | 60 | 11 | LoanStream programs (attributes as rows, intermediate) |
| `scripts` | - | 7 | Stored Python query scripts |

**Key Structure:**
- **programs_v3**: Rows = Programs, Columns = Attributes ✓
- **16 programs total**: 9 PRMG + 7 LoanStream
- **60 attributes per program**: Credit scores, loan amounts, LTV, DTI, etc.
- **Clean expressions**: Ready for LLM processing (e.g., `>=660`, `if ltv>85%, then <=45%`)
- **Data Source**: `data/v3/Non-QM_Matrix.xlsx - Attributes.tsv`

#### Data Refresh

When source data is updated:

```bash
python utils/convert_v3_to_sqlite.py && python utils/transpose_v3_tables.py
```

This creates the `programs_v3` table (16 programs × 62 attributes) from `data/v3/Non-QM_Matrix.xlsx - Attributes.tsv`

### 2. Script Management System

Store and execute Python scripts without creating files. Scripts are stored in the database with natural language prompts for semantic matching.

#### Scripts Table Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Auto-incrementing primary key |
| `name` | TEXT | Unique script name |
| `description` | TEXT | Human-readable description |
| `script` | TEXT | Python code to execute |
| `prompt` | TEXT | Natural language pattern for matching |
| `created_at` | TIMESTAMP | Creation timestamp |
| `updated_at` | TIMESTAMP | Last modification timestamp |

#### Available Scripts

| Script | Description | Context Behavior |
|--------|-------------|------------------|
| `show_programs` | List all programs for a servicer | No context needed (starting point) |
| `find_program_params` | Get all parameters and values for a program | ✓ Auto-selects queried program |
| `get_param_value` | Get specific parameter value | ✓ Auto-selects queried program |
| `show_program_parameters` | List parameter names only | ✓ Auto-selects queried program |
| `match_programs` | Match borrower criteria to eligible programs | ✓ Filters by selected_programs |
| `find_param_across_programs` | Find parameter across multiple programs | ✓ Filters by selected_programs |

**Context Behavior:**
- **Auto-selects**: Single-program queries automatically select that program for subsequent queries
- **Filters by selected_programs**: Multi-program queries respect the selected program context
- **No context needed**: Starting point queries that list all programs

#### Script Management Commands

```bash
# List all scripts
python utils/run_script.py --list

# Run a script
python utils/run_script.py show_programs

# View script code
python utils/run_script.py --show show_programs

# Add new script interactively
python utils/manage_scripts.py add

# Delete a script
python utils/manage_scripts.py delete <script_name>
```

### 3. Natural Language Query Parser

**Production-Ready** with **100% test pass rate** (5/5 tests passed)

#### Features

- **Semantic matching** using sentence-transformers (all-mpnet-base-v2)
- **Automatic parameter extraction** (loan_servicer, program_name, param_name)
- **Loan servicer inference** (PRMG/xxx → Prime, LoanStream-xxx → LoanStream)
- **Query execution** with SQLite database
- **Clean output formatting** for LLM consumption

#### Parsers Available

- `src/parser.py` - **Sentence-transformers** (Production, 100% accuracy)
- `src/parser_qwen.py` - Qwen1.5-0.5B (Alternative, not tested)

#### Query Examples

```bash
# List programs
python3 src/parser.py "show programs for Prime"
# Output: Lists 9 PRMG programs

# Get program details
python3 src/parser.py "find all parameters for PRMG/Prime Connect"
# Output: 43 non-empty parameters with clean expressions

# Get specific parameter
python3 src/parser.py "show borrower_credit_score in Prime programs"
# Output: Credit score requirements across Prime programs

# Match borrower to programs
python3 src/parser.py "match programs for 680 credit score, $500000 loan amount"
# Output: Eligible programs with match percentages
```

#### Query Format Tips

- ✓ `"show programs for [Prime|LoanStream]"`
- ✓ `"find all parameters for [program name]"`
- ✓ `"show [parameter] in [Prime|LoanStream] programs"`
- ✓ `"match programs for [borrower criteria]"`

### 4. Electron App with Context-Aware Program Selection

#### Design Objective

**NO MATTER HOW PROGRAMS ARE FILTERED, SUBSEQUENT ACTIONS RUN ON SELECTED PROGRAMS**

The app supports two distinct query flows with intelligent program selection:

#### Flow 1: Borrower Profile Matching
```
Load Borrower → Find Matching Programs → Programs appear as cards (auto-selected) →
Run subsequent queries → Only evaluates the auto-selected matched programs
(User can manually adjust selection by clicking cards or pressing ESC to clear)
```

#### Flow 2: Text Query Discovery
```
Text Query → Programs appear as cards → Select programs → Run queries on selection

OR

Single-Program Query → Program auto-selects → Subsequent queries use that program
```

#### Features

**Auto-Selection (Two Types)**

*Type 1: Borrower Matching Results*
- Click "Find Matching Programs" → Results auto-select
- All matched programs immediately have selection indicators
- Subsequent queries operate on matched subset only
- User can adjust selection by clicking cards

*Type 2: Single-Program Queries*
- Query specific program (e.g., `^ find all parameters for PRMG/Prime Connect`)
- That program auto-selects itself
- Subsequent queries operate in context of that program
- User sees visual selection indicators immediately

**Manual Selection & Context**
- Click program cards to toggle selection (multi-select supported)
- Selected programs provide context for ALL subsequent queries
- Press `ESC` anywhere in UI to clear all selections
- Visual indicators: ring border, checkboxes, selection badge

**Natural Language Interface**
- Query input with `^` prefix for script execution
- Chat-style query history with results
- Context badges show selected programs in queries

**Program Matching**
- Load borrower profile (sample or custom)
- Match button finds eligible programs
- Results show match scores and program details

#### Starting the Electron App

```bash
cd electron-loan-app
npm start
```

#### Usage Flow Examples

**Flow 1: Borrower Matching with Auto-Selection**

1. **Load Borrower**: Click "Sample Borrower" to load test profile
2. **Find Matches**: Click "Find Matching Programs" → Get 3-12 eligible programs
3. **Auto-Selected**: All matched programs automatically select (ring borders, checkboxes, badge)
4. **Query with Context**:
   ```
   Query: ^ match programs for 680 credit score
   Result: Only evaluates the auto-selected matched programs (not all 16)
   ```
5. **Adjust Selection** (Optional): Click cards to deselect, or ESC to clear all

**Flow 2: Text Query with Manual Selection**

1. **List Programs**:
   ```
   Query: ^ show programs for Prime
   Result: 9 PRMG program cards appear
   ```
2. **Select Programs**: Click 3 cards → Badge shows "3 selected"
3. **Query with Context**:
   ```
   Query: ^ find ltv across Prime programs
   Result: Shows LTV values for the 3 selected programs only
   ```

**Flow 3: Single-Program Auto-Selection**

1. **Query Specific Program**:
   ```
   Query: ^ find all parameters for PRMG/Prime Connect
   Result: Program auto-selects, shows 43 parameters
   ```
2. **Subsequent Query Uses Context**:
   ```
   Query: ^ find borrower_credit_score across Prime programs
   Result: Shows credit score for PRMG/Prime Connect only
   ```

**Clear Selection Anytime**
   - Press `ESC` key anywhere in UI
   - Visual feedback: "Selection Cleared"
   - All indicators removed

#### Program Selection API

JavaScript functions available in `window.appFunctions`:

```javascript
// Toggle program selection
toggleProgramSelection(programName, servicer)

// Update selection count badge
updateSelectionIndicator()

// Clear all selections
clearProgramSelection()

// Get selected programs as array
getSelectedPrograms() // Returns: [{ servicer, programName }, ...]
```

#### Technical Implementation

**Context Flow Architecture** (Proper LLM Context Passing):
```
Frontend (index.html)
  ↓ selectedPrograms Set
HTMX Interceptor
  ↓ JSON in request body
Backend (query.js)
  ↓ contextParams object: { selected_programs: [...], selected_servicers: [...] }
Python Bridge (python-bridge.js)
  ↓ QUERY_CONTEXT environment variable
Parser (parser.py)
  ↓ Merges context into globals()
Scripts (match_programs, find_param_across_programs)
  ↓ Read selected_programs from globals()
  ↓ Filter SQL queries accordingly
```

**Frontend** (`electron-loan-app/src/index.html`):
- Selection state: `window.selectedPrograms` (JavaScript Set)
- Key format: `${servicer}::${programName}`
- HTMX interceptor adds `selectedPrograms` JSON to POST request
- ESC key handler for clearing selections
- Auto-selection: Receives inline `<script>` from backend for single-program queries

**Backend** (`electron-loan-app/src/server/routes/query.js`):
- Parses `selectedPrograms` from request → creates `contextParams` object
- Passes context to Python bridge via environment variable
- Detects single-program queries → returns `autoSelectProgram` metadata
- Injects auto-selection JavaScript for single-program results
- Generates structured HTML with program cards

**Python Layer**:
- **Parser** (`src/parser.py`): Reads `QUERY_CONTEXT` from environment, merges into script execution scope
- **Scripts**: Access context via `globals().get('selected_programs', None)`
  - **match_programs**: Filters programs by `selected_programs` before matching
  - **find_param_across_programs**: Shows parameter values for selected programs only

**Result Parsers**:
- `parseProgramList()` - Program listings with selectable cards
- `parseMatchingPrograms()` - Match results with scores and selection
- `parseParameterList()` - Parameter tables (triggers auto-selection)
- `parseParameterValue()` - Parameter details (triggers auto-selection)
- `parseGenericResults()` - Fallback for unknown formats

**Context-Aware Scripts**:
- ✅ `match_programs` - Filters by selected_programs
- ✅ `find_param_across_programs` - Filters by selected_programs
- ✅ `find_program_params` - Triggers auto-selection
- ✅ `get_param_value` - Triggers auto-selection
- ✅ `show_program_parameters` - Triggers auto-selection
- ℹ️ `show_programs` - Starting point, shows all programs

## Testing & Verification

### Database Scripts Testing (5/5 Passed)

All scripts tested successfully with production `programs_v3` table:

| Test | Script | Result |
|------|--------|--------|
| 1 | show_programs | ✓ Lists 9 Prime programs |
| 2 | find_program_params | ✓ Shows 43 parameters |
| 3 | get_param_value | ✓ Gets credit score value |
| 4 | show_program_parameters | ✓ Lists 43 parameter names |
| 5 | match_programs | ✓ Matches 12 eligible programs |

**Test Date**: 2025-10-13
**Database**: programs_v3 (current production data)

### Natural Language Parser Testing (5/5 Passed)

| Test | Query | Script Matched | Result |
|------|-------|----------------|--------|
| 1 | "show programs for Prime" | show_programs (0.465) | ✓ 9 programs |
| 2 | "show programs for LoanStream" | show_programs (0.781) | ✓ 7 programs |
| 3 | "find all parameters for PRMG/Prime Connect" | find_program_params (0.485) | ✓ 43 params |
| 4 | "find borrower_credit_score across Prime" | match_programs (0.505) | ✓ Works |
| 5 | "show all parameters supported by PRMG/Plus Connect" | show_program_parameters (0.572) | ✓ 60 params |

**Test Date**: 2025-10-13
**Parser**: sentence-transformers (src/parser.py)
**Database**: programs_v3
**Success Rate**: 100%

### Electron App Testing

#### Context-Aware Flow Testing

**Test 1: Borrower Matching with Auto-Selection**
1. Load sample borrower (680 credit, $500k loan, 75% LTV)
2. Click "Find Matching Programs" → Get 12 matches
3. **Verify**: All 12 programs auto-select (ring borders, checkboxes, "12 selected" badge)
4. Query: `^ match programs for 680 credit score`
5. **Expected**: Only evaluates the 12 selected programs, shows "Filtered by Selected Programs (12): ..."

**Test 2: Text Query with Manual Selection**
1. Query: `^ show Prime programs`
2. Select 3 program cards → Badge shows "3 selected"
3. Query: `^ find ltv across Prime programs`
4. **Expected**: Shows LTV for 3 selected programs only, output includes "Filtered by Selected Programs: 3"

**Test 3: Single-Program Auto-Selection**
1. Query: `^ find all parameters for PRMG/Prime Connect`
2. **Expected**: Program auto-selects, shows selection indicators
3. Query: `^ find borrower_credit_score across Prime programs`
4. **Expected**: Shows credit score for PRMG/Prime Connect only

**Test 4: ESC Key Clears Context**
1. After any selection (manual or auto)
2. Press `ESC` key anywhere in UI
3. **Expected**: "Selection Cleared" message, all indicators removed
4. Next query runs across all programs (no context)

**Test 5: Context Persistence**
1. Select 2 programs
2. Run multiple queries
3. **Expected**: All queries respect the same 2 selected programs
4. Press ESC → Context clears
5. Next query runs without context

See `electron-loan-app/TESTING_GUIDE.md` for additional test scenarios including:
- Browser console debugging
- Network request inspection
- Error handling

## Usage Examples

### Example 1: Program Discovery

```bash
# List all Prime programs
python3 src/parser.py "show programs for Prime"

# Output:
# 1. PRMG/Prime Connect
# 2. PRMG/Plus Connect
# 3. PRMG/Flex Connect Prime
# ... (9 total)
```

### Example 2: Program Details

```bash
# Get all parameters for a program
python3 src/parser.py "find all parameters for PRMG/Prime Connect"

# Output:
# borrower_credit_score: >=660
# dti: if ltv,cltv>85%, then <=45% if ltv,cltv<=85%, then <=50%
# loan_amount: >=125000 and <=3500000
# ... (43 parameters total)
```

### Example 3: Borrower Matching

```bash
# Match borrower to eligible programs
python3 src/parser.py "match programs for 680 credit score, $500000 loan amount, 75% LTV"

# Output:
# ELIGIBLE PROGRAMS (12):
# PRMG/Prime Connect (Prime) - 100.0% match
# PRMG/Plus Connect (Prime) - 100.0% match
# ... (12 total matches)
```

### Example 4: Context-Aware Queries (Electron App)

**Scenario 1: Manual Selection**
1. **List programs**: `^ show programs for Prime` → 9 cards appear
2. **Select programs**: Click "PRMG/Prime Connect" and "PRMG/Plus Connect"
3. **Query with context**: `^ find borrower_credit_score across Prime programs`
4. **Result**: Shows credit scores for the 2 selected programs only

**Scenario 2: Auto-Selection**
1. **Query specific program**: `^ find all parameters for PRMG/Prime Connect`
2. **Auto-selects**: Program automatically selects itself
3. **Subsequent query**: `^ match programs for 680 credit score`
4. **Result**: Evaluates only PRMG/Prime Connect (the selected program)

**Scenario 3: Borrower Matching**
1. **Load borrower**: Click "Sample Borrower"
2. **Find matches**: Click "Find Matching Programs" → Get 12 eligible programs
3. **Select subset**: Click 3 specific programs
4. **Query with context**: `^ match programs for 700 credit score`
5. **Result**: Re-evaluates only the 3 selected programs with new criteria

## Development Notes

### Parser Improvements Applied

**October 2025**:
- ✓ Added "by <program_name>" pattern recognition
- ✓ Automatic loan_servicer inference from program names
  - PRMG/xxx → Prime
  - LoanStream-xxx → LoanStream
- ✓ 100% test pass rate achieved

### Electron App Features Added

**October 2025**:
- ✓ **Context-aware program selection** (two-flow design)
  - Flow 1: Borrower matching → **Auto-selects results** → Context-aware queries
  - Flow 2: Text query → Manual selection → Context-aware queries
- ✓ **Auto-selection (two types)**
  - Type 1: Borrower matching results auto-select all matched programs
  - Type 2: Single-program queries auto-select the queried program
  - Subsequent queries operate in context of auto-selected programs
- ✓ **Proper LLM context passing** (not string manipulation)
  - Context flows: Frontend → Backend → Python → Scripts via environment variables
  - Scripts access context via `globals().get('selected_programs')`
- ✓ **Context-aware script execution**
  - `match_programs`: Filters by selected_programs before matching
  - `find_param_across_programs`: Shows values for selected programs only
- ✓ **Visual selection indicators**
  - Ring border, checkboxes, selection badge
  - ESC key handler for clearing selections anywhere in UI
- ✓ **Match results parser** with score badges
- ✓ **Help tooltips** and user guidance

### Data Structure

**Production Structure** (programs_v3):
- **Rows** = Programs (16 total)
- **Columns** = Attributes (62 total)
- **Format**: One program per row, one attribute per column
- **Source**: `data/v3/Non-QM_Matrix.xlsx - Attributes.tsv`

**Intermediate Structure** (prime_v3, loanstream_v3):
- **Rows** = Attributes (60 total)
- **Columns** = Programs (9 Prime or 7 LoanStream)
- **Purpose**: Transposed to create programs_v3

### Production Configuration

1. ✓ Use `programs_v3` for all queries (current production data)
2. ✓ Use `src/parser.py` (sentence-transformers) for natural language queries
3. ✓ Refresh data by running conversion scripts when source TSV is updated
4. ✓ All scripts and electron app use programs_v3
5. Test Qwen parser (parser_qwen.py) as alternative if needed

### Future Enhancements

#### Database
- [ ] Add program version tracking
- [ ] Add audit trail for data changes
- [ ] Add program comparison queries

#### Parser
- [ ] Add fuzzy matching for program names
- [ ] Add query history and suggestions
- [ ] Add multi-criteria ranking

#### Electron App
- [x] Context-aware program selection (completed)
- [x] Auto-selection for single-program queries (completed)
- [x] ESC key to clear selections (completed)
- [ ] Persist selection across page refreshes (localStorage)
- [ ] Add "Select All" / "Deselect All" buttons
- [ ] Add program comparison view
- [ ] Add export to PDF/Excel
- [ ] Add borrower profile saving

## System Architecture

### Data Layer
- **SQLite Database**: `loanpilot.db` with `programs_v3` table (16 programs × 62 attributes)
- **Data Source**: `data/v3/Non-QM_Matrix.xlsx - Attributes.tsv`
- **Refresh Command**: `python utils/convert_v3_to_sqlite.py && python utils/transpose_v3_tables.py`

### Query Layer
- **Parser**: `src/parser.py` using sentence-transformers (all-mpnet-base-v2)
- **Script Storage**: Database-backed with natural language prompts
- **Execution**: Python scripts executed via `exec()` with context injection

### Application Layer
- **Electron Desktop App**: HTMX-powered interactive UI
- **Backend**: Express.js with Python bridge
- **Frontend**: TailwindCSS + DaisyUI with JavaScript

### Context Flow
```
User Selection → Frontend Set → HTMX Interceptor → Backend contextParams →
Python Bridge (env var) → Parser (globals merge) → Script Execution (filtered queries)
```

## Current Implementation Status

### ✅ Completed Features

**Database & Scripts**
- [x] SQLite programs_v3 table (16 programs, 62 attributes)
- [x] Script management system (6 stored scripts)
- [x] Context-aware script execution
- [x] Natural language query parser (100% test pass rate)

**Electron App**
- [x] Two-flow program selection architecture
- [x] Auto-selection for borrower matching results (Type 1)
- [x] Auto-selection for single-program queries (Type 2)
- [x] Manual multi-select with visual indicators
- [x] Context-aware query execution
- [x] ESC key to clear selections
- [x] Program matching with borrower profiles
- [x] Rich program cards with details

**Context System**
- [x] Proper LLM context passing (environment variables)
- [x] Scripts access context via `globals().get('selected_programs')`
- [x] Auto-selection of borrower matching results
- [x] Auto-selection trigger for single-program queries
- [x] Context filtering in `match_programs` script
- [x] Context filtering in `find_param_across_programs` script

### 📊 Test Results (Latest)

**Database Scripts**: 5/5 passed
**Parser Accuracy**: 100% (5/5 queries matched correctly)
**Context-Aware Flows**: Both flows verified working

## Deployment Options

### 🐳 Docker (Recommended for Production)

**Best for**: Cloud deployments, consistent environments, easy updates

- One-command deployment with `docker-compose`
- Automatic dependency management
- Data persistence with volumes
- Health checks and auto-restart
- Easy scaling and updates

**Guides**:
- [DOCKER_QUICKSTART.md](DOCKER_QUICKSTART.md) - Quick start guide
- [DOCKER_DEPLOYMENT_GUIDE.md](DOCKER_DEPLOYMENT_GUIDE.md) - Comprehensive deployment guide

### ☁️ AWS EC2 (Direct Installation)

**Best for**: Custom configurations, existing infrastructure

- Direct Python installation
- Manual dependency management
- Full control over environment

**Guide**: [loanpilot_aws_deployment.md](loanpilot_aws_deployment.md)

### 💻 Local Development

**Best for**: Development and testing

```bash
pip install -r requirements.txt
python utils/convert_v3_to_sqlite.py
cd web-app
PYTHONPATH='..:.' python3 -m uvicorn main:app --reload
```

## Documentation

### User Guides
- [PROGRAM_UPLOAD_GUIDE.md](PROGRAM_UPLOAD_GUIDE.md) - Upload new loan programs
- [DATABASE_RESET_GUIDE.md](DATABASE_RESET_GUIDE.md) - Database management and backups

### Technical Documentation
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - Detailed architecture
- [loanpilot_aws_deployment.md](loanpilot_aws_deployment.md) - AWS deployment guide
- [DOCKER_DEPLOYMENT_GUIDE.md](DOCKER_DEPLOYMENT_GUIDE.md) - Docker deployment guide

### Design Documents
- [docs/design.md](docs/design.md) - System design
- [docs/parameter_analysis.md](docs/parameter_analysis.md) - Parameter analysis
- [docs/ba_parameter_guide.md](docs/ba_parameter_guide.md) - Business analyst guide

## License

Internal use only.
