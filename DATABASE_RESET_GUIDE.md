# Database Reset Feature - User Guide

## Overview

The Database Reset feature allows you to safely reset the LoanPilot database to its original state, removing all custom programs and restoring the baseline data from the source TSV file.

## Key Features

- **Automatic Backup**: Creates timestamped backups before any destructive operation
- **Complete Reset**: Drops all tables and repopulates from source TSV
- **Backup Management**: List, create, and restore from backups
- **Database Info**: View current database state and statistics
- **Safety Checks**: Confirmation dialogs and automatic backups prevent data loss

## Access Database Management

Click the **"Database"** dropdown in the header to access:

1. **Database Info** - View current database statistics
2. **Manage Backups** - Create, list, and restore backups
3. **Reset Database** - Complete database reset (Danger Zone)

---

## 1. View Database Information

**Purpose**: Check current database state before making changes

**Steps**:
1. Click **Database** → **Database Info**
2. View statistics:
   - Database size (KB)
   - Total tables
   - Total programs (Prime + LoanStream)
   - Table list with row counts

**Example Output**:
```
Database Size: 552 KB
Total Tables: 13
Total Programs: 17
  - Prime: 10 programs
  - LoanStream: 7 programs

Tables:
  prime_v3: 60 rows
  loanstream_v3: 60 rows
  scripts: 12 rows
  ... (etc)
```

---

## 2. Create Manual Backup

**Purpose**: Create a backup before testing or making risky changes

**Steps**:
1. Click **Database** → **Manage Backups**
2. Click **"Create Backup"** button
3. Wait for confirmation
4. Backup appears in the list with timestamp

**Backup Naming**:
```
loanpilot_backup_YYYYMMDD_HHMMSS.db
Example: loanpilot_backup_20251118_143052.db
```

**Backup Location**: `backups/` directory (auto-created)

**When to Create Manual Backups**:
- Before importing multiple programs
- Before testing new features
- At the end of each day/week
- Before major data changes

---

## 3. Restore from Backup

**Purpose**: Revert database to a previous state

**Steps**:
1. Click **Database** → **Manage Backups**
2. Browse available backups (sorted newest first)
3. Click **"Restore"** button next to desired backup
4. Confirm the restoration
5. Wait for process to complete
6. Page reloads automatically with restored data

**Safety**:
- Current database is backed up **before** restore
- Original backup file is preserved
- You get two copies: current (before restore) + restored state

**Restore Flow**:
```
1. User selects backup: loanpilot_backup_20251118_120000.db
2. System creates safety backup: loanpilot_backup_20251118_143055.db
3. System restores from selected backup
4. Result: Database at 12:00:00 state
5. Safety backup available if needed: 14:30:55 state
```

---

## 4. Reset Database

**Purpose**: Remove all custom programs and return to baseline state

### ⚠️ WARNING

**This operation will**:
- Drop ALL database tables
- Delete ALL uploaded programs
- Remove ALL custom data
- Repopulate from original TSV file (baseline data only)

**This operation will NOT affect**:
- The source TSV file (data/v3/Non-QM_Matrix.xlsx - Attributes.tsv)
- Backup files (they remain safe)
- Application code or configuration

### When to Reset

- After testing with many uploaded programs
- To return to clean baseline state
- When database becomes corrupted
- To start fresh with original data

### Reset Steps

1. **Click Database → Reset Database**

2. **Review Warning**:
   ```
   This action will:
   - Drop all database tables
   - Delete all uploaded programs
   - Repopulate with original data from TSV

   A backup will be created automatically before resetting.
   ```

3. **Choose Backup Option**:
   - ☑️ **Create backup before reset** (recommended, checked by default)
   - ☐ Skip backup (only if you have recent backups)

4. **Click "Reset Database"** button

5. **Wait for Process**:
   - Backup creation (if enabled)
   - Drop all tables
   - Repopulate from TSV
   - Progress shown in real-time

6. **View Confirmation**:
   ```
   Database Reset Complete!
   Backup: loanpilot_backup_20251118_143500.db
   Repopulated: 9 Prime + 7 LoanStream programs
   ```

7. **Page Reloads Automatically**

### Reset Process Details

The reset follows this sequence:

```
Step 1: Get Database Info
  → Current state captured for logging

Step 2: Create Backup (if enabled)
  → loanpilot_backup_YYYYMMDD_HHMMSS.db
  → Stored in backups/ directory

Step 3: Drop All Tables
  → prime_v3, loanstream_v3, scripts, etc.
  → All tables removed from database

Step 4: Repopulate from TSV
  → Read: data/v3/Non-QM_Matrix.xlsx - Attributes.tsv
  → Normalize line endings
  → Parse TSV structure
  → Create prime_v3 table (9 PRMG programs)
  → Create loanstream_v3 table (7 LoanStream programs)
  → 60 attributes × 16 programs populated

Step 5: Verify Success
  → Get new database info
  → Confirm tables created
  → Log results
```

---

## API Endpoints

For programmatic access:

### Get Database Info
```http
GET /api/database/info

Response:
{
  "success": true,
  "database": {
    "exists": true,
    "size_kb": 552.0,
    "tables": {"prime_v3": 60, "loanstream_v3": 60, ...},
    "total_tables": 13,
    "program_counts": {"Prime": 9, "LoanStream": 7},
    "total_programs": 16
  }
}
```

### List Backups
```http
GET /api/database/backups

Response:
{
  "success": true,
  "backups": [
    {
      "name": "loanpilot_backup_20251118_143052.db",
      "path": "backups/loanpilot_backup_20251118_143052.db",
      "size_kb": 552.0,
      "created": "2025-11-18T14:30:52"
    }
  ],
  "count": 1
}
```

### Create Backup
```http
POST /api/database/backup

Response:
{
  "success": true,
  "backup_path": "backups/loanpilot_backup_20251118_143052.db",
  "backup_name": "loanpilot_backup_20251118_143052.db",
  "size_kb": 552.0,
  "timestamp": "20251118_143052"
}
```

### Restore Backup
```http
POST /api/database/restore
Content-Type: multipart/form-data

backup_name=loanpilot_backup_20251118_143052.db

Response:
{
  "success": true,
  "message": "Database restored from loanpilot_backup_20251118_143052.db",
  "current_backup": "loanpilot_backup_20251118_143055.db"
}
```

### Reset Database
```http
POST /api/database/reset
Content-Type: multipart/form-data

create_backup=true

Response:
{
  "success": true,
  "message": "Database reset completed successfully",
  "steps": [
    {"step": "info", "success": true, "data": {...}},
    {"step": "backup", "success": true, "data": {...}},
    {"step": "drop_tables", "success": true, "data": {...}},
    {"step": "repopulate", "success": true, "data": {...}}
  ],
  "new_state": {...}
}
```

---

## Troubleshooting

### Problem: "Backup failed"

**Possible Causes**:
- Disk full
- Permission issues
- Database locked

**Solutions**:
```bash
# Check disk space
df -h

# Check backup directory permissions
ls -ld backups/
chmod 755 backups/

# Check database file
ls -l loanpilot.db
```

### Problem: "Repopulation failed"

**Possible Causes**:
- TSV file missing
- TSV file corrupted
- Pandas not installed

**Solutions**:
```bash
# Verify TSV exists
ls -l data/v3/Non-QM_Matrix.xlsx\ -\ Attributes.tsv

# Check pandas
python3 -c "import pandas; print('OK')"

# Verify TSV format
head -5 data/v3/Non-QM_Matrix.xlsx\ -\ Attributes.tsv
```

### Problem: "Reset hangs or times out"

**Solution**:
- Check server logs: `web-app/logs/loanpilot.log`
- Database may be locked by another process
- Restart the application

```bash
# Check for running processes
ps aux | grep uvicorn

# Stop application
pkill -f uvicorn

# Restart
cd web-app
PYTHONPATH='..:.' python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Problem: "Restore doesn't work"

**Checklist**:
- Backup file exists in `backups/` directory
- Backup file is valid SQLite database
- Sufficient disk space
- No permission issues

```bash
# Verify backup is valid SQLite
sqlite3 backups/loanpilot_backup_TIMESTAMP.db "SELECT COUNT(*) FROM sqlite_master"

# Check file permissions
ls -l backups/
```

---

## Best Practices

### 1. **Backup Strategy**

**Before Major Changes**:
```
✓ Before uploading 10+ programs
✓ Before testing new features
✓ Before database reset
```

**Regular Backups**:
```
✓ Daily: if actively developing
✓ Weekly: if in production
✓ After each major milestone
```

**Retention Policy**:
```
- Keep last 7 daily backups
- Keep last 4 weekly backups
- Keep monthly backups for 1 year
```

### 2. **Reset Usage**

**When to Reset**:
- After completing a testing cycle
- Database has too many test programs
- Need fresh start
- Database corruption suspected

**When NOT to Reset**:
- Production environment with live data
- Custom programs are valuable
- No recent backup exists
- Unsure about consequences

### 3. **Testing Workflow**

**Recommended Flow**:
```
1. Create backup before testing
2. Upload/test programs
3. Review results
4. If satisfied: Keep changes
5. If not satisfied: Restore backup or reset
```

### 4. **Production Safety**

**Protection Checklist**:
```
☐ Latest backup confirmed
☐ Backup tested (can restore successfully)
☐ Users notified of downtime
☐ Database info exported if needed
☐ Rollback plan ready
```

---

## Command-Line Management

For direct database management:

### Create Backup Manually
```bash
cp loanpilot.db "backups/loanpilot_backup_$(date +%Y%m%d_%H%M%S).db"
```

### List Backups
```bash
ls -lh backups/
```

### Restore Manually
```bash
# Backup current
cp loanpilot.db loanpilot_current_backup.db

# Restore from backup
cp backups/loanpilot_backup_20251118_143052.db loanpilot.db
```

### Reset Manually
```bash
# Backup first
cp loanpilot.db "backups/loanpilot_before_reset_$(date +%Y%m%d_%H%M%S).db"

# Run reset script
python3 utils/convert_v3_to_sqlite.py
```

---

## Technical Details

### DatabaseManager Class

Located in: `web-app/database_manager.py`

**Methods**:
- `create_backup()` - Create timestamped backup
- `list_backups()` - List all backups (sorted newest first)
- `restore_backup(name)` - Restore from specific backup
- `get_database_info()` - Get current database stats
- `drop_all_tables()` - Drop all tables (internal)
- `repopulate_from_tsv()` - Repopulate from TSV (internal)
- `reset_database(create_backup)` - Complete reset flow

### Backup Directory Structure

```
loanpilot/
├── loanpilot.db (active database)
├── backups/
│   ├── loanpilot_backup_20251118_090000.db
│   ├── loanpilot_backup_20251118_120000.db
│   ├── loanpilot_backup_20251118_143052.db
│   └── ... (more backups)
└── data/
    └── v3/
        └── Non-QM_Matrix.xlsx - Attributes.tsv (source data)
```

### Safety Mechanisms

1. **Automatic Backups**: Reset creates backup by default
2. **Pre-Restore Backups**: Restore backs up current state
3. **Confirmation Dialogs**: User must confirm destructive operations
4. **Error Handling**: Detailed error messages and rollback on failure
5. **Atomic Operations**: Database changes are committed as transactions
6. **Backup Preservation**: Original backups never modified

---

## Related Documentation

- [PROGRAM_UPLOAD_GUIDE.md](PROGRAM_UPLOAD_GUIDE.md) - Upload new programs
- [README.md](README.md) - Main project overview
- [loanpilot_aws_deployment.md](loanpilot_aws_deployment.md) - Deployment guide

---

## Quick Reference Card

| Action | Steps | Safety Level |
|--------|-------|--------------|
| **View Info** | Database → Info | ✅ Safe |
| **Create Backup** | Database → Backups → Create | ✅ Safe |
| **Restore Backup** | Database → Backups → Restore | ⚠️ Creates safety backup first |
| **Reset Database** | Database → Reset → Confirm | ⚠️ Creates backup by default |

**Remember**: When in doubt, create a backup first!
