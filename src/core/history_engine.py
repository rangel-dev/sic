import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core import telemetry

DB_NAME = "history.db"

class HistoryEngine:
    @staticmethod
    def _get_connection():
        # Get the path relative to the project root (3 levels up from src/core/history_engine.py)
        db_path = Path(__file__).parent.parent.parent / DB_NAME
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # Colunas de contagem padronizada de erro/acerto (Tarefa 7). Adicionadas
    # via ALTER TABLE em bancos antigos; linhas anteriores ficam NULL, o que
    # significa "sem contagem" — consumidores devem ignorar NULL, não somar 0.
    _COUNT_COLUMNS = (
        ("status", "TEXT"),        # "ok" (rodou até o fim) | "falha"
        ("ok_count", "INTEGER"),   # itens com acerto (NULL = módulo sem essa noção)
        ("error_count", "INTEGER"),
        ("total", "INTEGER"),      # universo processado
        ("breakdown", "TEXT"),     # JSON {rótulo do tipo de erro: contagem} (Tarefa 8)
    )

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
            existing = {row["name"] for row in conn.execute("PRAGMA table_info(history)")}
            for col_name, col_type in HistoryEngine._COUNT_COLUMNS:
                if col_name not in existing:
                    conn.execute(f"ALTER TABLE history ADD COLUMN {col_name} {col_type}")
            conn.commit()

    @staticmethod
    def add_entry(
        module: str,
        brand: str,
        action: str,
        details: str = "",
        *,
        status: str = "ok",
        ok_count: Optional[int] = None,
        error_count: Optional[int] = None,
        total: Optional[int] = None,
        breakdown: Optional[dict] = None,
    ):
        """Adds a new entry to the history."""
        # Ensure DB is initialized
        HistoryEngine.init_db()

        breakdown_json = (
            json.dumps(breakdown, ensure_ascii=False) if breakdown else None
        )
        timestamp = datetime.now().isoformat()
        with HistoryEngine._get_connection() as conn:
            conn.execute(
                "INSERT INTO history (timestamp, module, brand, action, details, "
                "status, ok_count, error_count, total, breakdown) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (timestamp, module, brand, action, details,
                 status, ok_count, error_count, total, breakdown_json)
            )
            conn.commit()

        # Telemetria de equipe (Tarefa 3) — melhor-esforço, nunca lança
        # exceção; grava só se a pasta compartilhada estiver configurada.
        telemetry.write_event(
            module, brand, action,
            status=status, ok_count=ok_count, error_count=error_count, total=total,
            breakdown=breakdown,
        )

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
