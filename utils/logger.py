"""
Logger System for Newton Smart Home Application
Logs all important events to data/logs.xlsx
"""

import os
import pandas as pd
from datetime import datetime
from typing import Optional
try:
    from utils import db as _db
except Exception:
    _db = None


def ensure_logs_file():
    """Create logs.xlsx if it doesn't exist."""
    os.makedirs("data", exist_ok=True)
    path = "data/logs.xlsx"
    if not os.path.exists(path):
        df = pd.DataFrame(columns=["timestamp", "user", "page", "action", "details"])
        df.to_excel(path, index=False)


def log_event(user: str, page: str, action: str, details: str = ""):
    """
    Log an event to data/logs.xlsx.
    
    Args:
        user: Username or "System"
        page: Page name (dashboard, quotation, etc.)
        action: Action type (login, logout, create, edit, delete, access, denied, etc.)
        details: Additional details about the event
    """
    try:
        # Try DB first (non-intrusive). Table 'logs' is optional in schema.
        if _db is not None:
            try:
                _db.db_execute('INSERT INTO logs("timestamp", "user", page, action, details) VALUES (%s,%s,%s,%s,%s)', (
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(user), str(page), str(action), str(details)
                ))
                return
            except Exception:
                # Fall back to Excel below
                pass

        ensure_logs_file()
        # Load existing logs
        try:
            logs = pd.read_excel("data/logs.xlsx")
        except:
            logs = pd.DataFrame(columns=["timestamp", "user", "page", "action", "details"])

        # Create new log entry
        new_log = pd.DataFrame([{
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user": str(user),
            "page": str(page),
            "action": str(action),
            "details": str(details)
        }])

        # Append and save
        logs = pd.concat([logs, new_log], ignore_index=True)
        logs.to_excel("data/logs.xlsx", index=False)
    except Exception as e:
        print(f"Error logging event: {e}")


def load_logs(filters: Optional[dict] = None) -> pd.DataFrame:
    """
    Load logs with optional filters.
    
    Args:
        filters: Dict with keys: user, page, action, date_from, date_to
    
    Returns:
        Filtered DataFrame
    """
    # Try DB first
    try:
        if _db is not None:
            try:
                rows = _db.db_query('SELECT timestamp, "user", page, action, details FROM logs ORDER BY timestamp DESC')
                df = pd.DataFrame(rows)
                df.columns = [c.strip().lower() for c in df.columns]
                logs = df
            except Exception:
                logs = None
        else:
            logs = None
    except Exception:
        logs = None

    if logs is None:
        # Excel fallback
        ensure_logs_file()
        try:
            logs = pd.read_excel("data/logs.xlsx")
            logs.columns = [c.strip().lower() for c in logs.columns]
        except Exception as e:
            print(f"Error loading logs: {e}")
            return pd.DataFrame(columns=["timestamp", "user", "page", "action", "details"])

    if filters:
        try:
            if filters.get("user"):
                logs = logs[logs["user"].str.contains(filters["user"], case=False, na=False)]
            if filters.get("page"):
                logs = logs[logs["page"].str.contains(filters["page"], case=False, na=False)]
            if filters.get("action"):
                logs = logs[logs["action"].str.contains(filters["action"], case=False, na=False)]
        except Exception:
            pass

    return logs.sort_values("timestamp", ascending=False) if "timestamp" in logs.columns else logs


def clear_old_logs(days: int = 90):
    """Delete logs older than specified days."""
    try:
        # Try DB delete if logs table exists
        if _db is not None:
            try:
                cutoff = (datetime.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
                _db.db_execute('DELETE FROM logs WHERE "timestamp" < %s', (cutoff,))
                return
            except Exception:
                pass

        logs = pd.read_excel("data/logs.xlsx")
        logs["timestamp"] = pd.to_datetime(logs["timestamp"])
        cutoff = datetime.now() - pd.Timedelta(days=days)
        logs = logs[logs["timestamp"] >= cutoff]
        logs.to_excel("data/logs.xlsx", index=False)
    except Exception as e:
        print(f"Error clearing old logs: {e}")
