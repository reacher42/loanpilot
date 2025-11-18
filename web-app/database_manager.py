#!/usr/bin/env python3
"""
Database Manager - Handle database reset and repopulation.
Provides safe reset functionality with backup and restore options.
"""

import sqlite3
import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
from io import StringIO


logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage database operations including reset and repopulation"""

    def __init__(self, db_path: str = "loanpilot.db", data_dir: str = "data/v3"):
        self.db_path = Path(db_path)
        self.data_dir = Path(data_dir)
        self.tsv_file = self.data_dir / "Non-QM_Matrix.xlsx - Attributes.tsv"
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)

    def create_backup(self) -> Dict:
        """
        Create a timestamped backup of the database.
        Returns backup info including path and size.
        """
        try:
            if not self.db_path.exists():
                return {
                    "success": False,
                    "error": "Database file does not exist"
                }

            # Create backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"loanpilot_backup_{timestamp}.db"

            # Copy database file
            shutil.copy2(self.db_path, backup_path)

            # Get file size
            size_bytes = backup_path.stat().st_size
            size_kb = size_bytes / 1024

            logger.info(f"✅ Database backup created: {backup_path.name} ({size_kb:.1f} KB)")

            return {
                "success": True,
                "backup_path": str(backup_path),
                "backup_name": backup_path.name,
                "size_kb": round(size_kb, 1),
                "timestamp": timestamp
            }

        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def list_backups(self) -> List[Dict]:
        """List all available database backups"""
        try:
            backups = []
            for backup_file in sorted(self.backup_dir.glob("loanpilot_backup_*.db"), reverse=True):
                stat = backup_file.stat()
                backups.append({
                    "name": backup_file.name,
                    "path": str(backup_file),
                    "size_kb": round(stat.st_size / 1024, 1),
                    "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

            return backups

        except Exception as e:
            logger.error(f"❌ Failed to list backups: {e}")
            return []

    def restore_backup(self, backup_name: str) -> Dict:
        """Restore database from a backup file"""
        try:
            backup_path = self.backup_dir / backup_name

            if not backup_path.exists():
                return {
                    "success": False,
                    "error": f"Backup file not found: {backup_name}"
                }

            # Create a backup of current database before restoring
            current_backup = self.create_backup()

            # Restore from backup
            shutil.copy2(backup_path, self.db_path)

            logger.info(f"✅ Database restored from: {backup_name}")

            return {
                "success": True,
                "message": f"Database restored from {backup_name}",
                "current_backup": current_backup.get("backup_name") if current_backup.get("success") else None
            }

        except Exception as e:
            logger.error(f"❌ Restore failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_database_info(self) -> Dict:
        """Get information about current database state"""
        try:
            if not self.db_path.exists():
                return {
                    "exists": False,
                    "error": "Database file does not exist"
                }

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get table list and row counts
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = {}

            for (table_name,) in cursor.fetchall():
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                tables[table_name] = count

            # Get program counts
            program_counts = {}
            if "prime_v3" in tables:
                cursor.execute("PRAGMA table_info(prime_v3)")
                prime_cols = len(cursor.fetchall()) - 4  # Subtract metadata columns
                program_counts["Prime"] = prime_cols

            if "loanstream_v3" in tables:
                cursor.execute("PRAGMA table_info(loanstream_v3)")
                loanstream_cols = len(cursor.fetchall()) - 4
                program_counts["LoanStream"] = loanstream_cols

            conn.close()

            # Get file size
            size_bytes = self.db_path.stat().st_size
            size_kb = size_bytes / 1024

            return {
                "exists": True,
                "size_kb": round(size_kb, 1),
                "tables": tables,
                "total_tables": len(tables),
                "program_counts": program_counts,
                "total_programs": sum(program_counts.values())
            }

        except Exception as e:
            logger.error(f"❌ Failed to get database info: {e}")
            return {
                "exists": self.db_path.exists(),
                "error": str(e)
            }

    def drop_all_tables(self) -> Dict:
        """Drop all tables from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get all table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            # Drop each table
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                logger.info(f"  Dropped table: {table}")

            conn.commit()
            conn.close()

            logger.info(f"✅ Dropped {len(tables)} tables")

            return {
                "success": True,
                "tables_dropped": tables,
                "count": len(tables)
            }

        except Exception as e:
            logger.error(f"❌ Failed to drop tables: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def repopulate_from_tsv(self) -> Dict:
        """Repopulate database from TSV file"""
        try:
            if not self.tsv_file.exists():
                return {
                    "success": False,
                    "error": f"TSV file not found: {self.tsv_file}"
                }

            logger.info(f"📥 Reading TSV data from {self.tsv_file.name}")

            # Read and normalize TSV content
            with open(self.tsv_file, 'rb') as f:
                binary_content = f.read()

            # Normalize line endings
            binary_content = binary_content.replace(b'\r\n', b'\n')
            binary_content = binary_content.replace(b'\r', b'')
            content = binary_content.decode('utf-8')

            # Parse TSV
            df = pd.read_csv(StringIO(content), sep='\t', engine='python', on_bad_lines='warn')

            logger.info(f"  Total rows: {len(df)}, Total columns: {len(df.columns)}")

            # Connect to database
            conn = sqlite3.connect(self.db_path)

            # Create prime_v3 table (metadata + PRMG programs)
            metadata_cols = df.columns[0:4].tolist()
            prmg_cols = df.columns[4:13].tolist()
            prime_v3_cols = metadata_cols + prmg_cols
            df_prime = df[prime_v3_cols].copy()

            logger.info(f"  Creating prime_v3 table with {len(prime_v3_cols)} columns")
            df_prime.to_sql('prime_v3', conn, if_exists='replace', index=False)

            # Create loanstream_v3 table (metadata + LoanStream programs)
            loanstream_cols = [col for col in df.columns if 'LoanStream' in col]
            loanstream_v3_cols = metadata_cols + loanstream_cols
            df_loanstream = df[loanstream_v3_cols].copy()

            logger.info(f"  Creating loanstream_v3 table with {len(loanstream_v3_cols)} columns")
            df_loanstream.to_sql('loanstream_v3', conn, if_exists='replace', index=False)

            conn.commit()
            conn.close()

            logger.info(f"✅ Database repopulated successfully")

            return {
                "success": True,
                "tables_created": ["prime_v3", "loanstream_v3"],
                "prime_programs": len(prmg_cols),
                "loanstream_programs": len(loanstream_cols),
                "total_attributes": len(df),
                "message": f"Repopulated with {len(prmg_cols)} Prime and {len(loanstream_cols)} LoanStream programs"
            }

        except Exception as e:
            logger.error(f"❌ Repopulation failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }

    def reset_database(self, create_backup: bool = True) -> Dict:
        """
        Complete database reset: backup, drop tables, repopulate.

        Args:
            create_backup: Whether to create a backup before resetting

        Returns:
            Dictionary with operation results
        """
        results = {
            "success": False,
            "steps": []
        }

        try:
            # Step 1: Get current database info
            logger.info("=" * 60)
            logger.info("DATABASE RESET STARTED")
            logger.info("=" * 60)

            db_info = self.get_database_info()
            results["steps"].append({
                "step": "info",
                "success": True,
                "data": db_info
            })

            # Step 2: Create backup (if requested)
            if create_backup and self.db_path.exists():
                logger.info("\n📦 Creating backup...")
                backup_result = self.create_backup()
                results["steps"].append({
                    "step": "backup",
                    "success": backup_result.get("success"),
                    "data": backup_result
                })

                if not backup_result.get("success"):
                    raise Exception(f"Backup failed: {backup_result.get('error')}")

            # Step 3: Drop all tables
            logger.info("\n🗑️  Dropping all tables...")
            drop_result = self.drop_all_tables()
            results["steps"].append({
                "step": "drop_tables",
                "success": drop_result.get("success"),
                "data": drop_result
            })

            if not drop_result.get("success"):
                raise Exception(f"Drop tables failed: {drop_result.get('error')}")

            # Step 4: Repopulate from TSV
            logger.info("\n📥 Repopulating from TSV...")
            repopulate_result = self.repopulate_from_tsv()
            results["steps"].append({
                "step": "repopulate",
                "success": repopulate_result.get("success"),
                "data": repopulate_result
            })

            if not repopulate_result.get("success"):
                raise Exception(f"Repopulation failed: {repopulate_result.get('error')}")

            # Success!
            results["success"] = True
            results["message"] = "Database reset completed successfully"

            logger.info("\n" + "=" * 60)
            logger.info("✅ DATABASE RESET COMPLETED")
            logger.info("=" * 60)

            # Get new database info
            new_db_info = self.get_database_info()
            results["new_state"] = new_db_info

            return results

        except Exception as e:
            logger.error(f"\n❌ Database reset failed: {e}")
            results["success"] = False
            results["error"] = str(e)
            return results


def main():
    """Test database reset functionality"""
    logging.basicConfig(level=logging.INFO)

    manager = DatabaseManager("../loanpilot.db", "../data/v3")

    # Get current info
    print("\n=== Current Database Info ===")
    info = manager.get_database_info()
    print(f"Exists: {info.get('exists')}")
    print(f"Tables: {info.get('total_tables')}")
    print(f"Programs: {info.get('program_counts')}")

    # List backups
    print("\n=== Available Backups ===")
    backups = manager.list_backups()
    for backup in backups[:5]:  # Show last 5
        print(f"  {backup['name']} - {backup['size_kb']} KB")

    # Test reset (uncomment to run)
    # print("\n=== Testing Reset ===")
    # result = manager.reset_database(create_backup=True)
    # print(f"Success: {result['success']}")
    # if result.get('message'):
    #     print(f"Message: {result['message']}")


if __name__ == "__main__":
    main()
