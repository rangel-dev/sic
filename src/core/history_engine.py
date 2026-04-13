import sqlite3
import os
from datetime import datetime
from pathlib import Path

DB_NAME = "history.db"

class HistoryEngine:
    @staticmethod
    def _get_connection():
        # Get the path relative to the project root (3 levels up from src/core/history_engine.py)
        db_path = Path(__file__).parent.parent.parent / DB_NAME
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def init_db():
        """Initializes the database and creates the history table if it doesn't exist."""
        with HistoryEngine._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    module TEXT NOT NULL,
                    brand TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT
                )
            """)
            conn.commit()

    @staticmethod
    def add_entry(module: str, brand: str, action: str, details: str = ""):
        """Adds a new entry to the history."""
        # Ensure DB is initialized
        HistoryEngine.init_db()
        
        timestamp = datetime.now().isoformat()
        with HistoryEngine._get_connection() as conn:
            conn.execute(
                "INSERT INTO history (timestamp, module, brand, action, details) VALUES (?, ?, ?, ?, ?)",
                (timestamp, module, brand, action, details)
            )
            conn.commit()

    @staticmethod
    def get_entries(
        start_date: str = None, 
        end_date: str = None, 
        brand: str = "all", 
        module: str = "all"
    ):
        """
        Retrieves entries filtered by date range, brand, and module.
        start_date and end_date should be in YYYY-MM-DD format.
        """
        HistoryEngine.init_db()
        
        query = "SELECT * FROM history WHERE 1=1"
        params = []

        if start_date:
            query += " AND date(timestamp) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND date(timestamp) <= ?"
            params.append(end_date)
            
        if brand != "all":
            if brand.lower() == "ambas":
                query += " AND (lower(brand) LIKE '%natura%' AND lower(brand) LIKE '%avon%')"
            else:
                query += " AND lower(brand) LIKE ?"
                params.append(f"%{brand.lower()}%")
            
        if module != "all":
            query += " AND lower(module) = ?"
            params.append(module.lower())

        query += " ORDER BY timestamp DESC"

        with HistoryEngine._get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    @staticmethod
    def delete_entry(entry_id: int):
        """Deletes a specific entry by ID."""
        with HistoryEngine._get_connection() as conn:
            conn.execute("DELETE FROM history WHERE id = ?", (entry_id,))
            conn.commit()

    @staticmethod
    def clear_history():
        """Removes all records from the history table."""
        with HistoryEngine._get_connection() as conn:
            conn.execute("DELETE FROM history")
            conn.commit()
