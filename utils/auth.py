"""
Authentication and User Management Utilities
Handles PIN-based login, user data, and permissions.
"""

import os
import pandas as pd
from typing import Optional, Dict
try:
    from utils import db as _db
except Exception:
    _db = None


def ensure_users_file():
    """Create users.xlsx if it doesn't exist with default admin user."""
    os.makedirs("data", exist_ok=True)
    path = "data/users.xlsx"
    if not os.path.exists(path):
        default_users = pd.DataFrame([
            {
                "name": "Admin",
                "pin": "1234",
                "role": "admin",
                "allowed_pages": "dashboard,quotation,invoice,receipt,customers,products,reports,archive,settings"
            },
            {
                "name": "Staff",
                "pin": "5678",
                "role": "staff",
                "allowed_pages": "dashboard,quotation,invoice,receipt,customers,archive"
            },
            {
                "name": "Viewer",
                "pin": "9999",
                "role": "viewer",
                "allowed_pages": "dashboard,reports"
            }
        ])
        default_users.to_excel(path, index=False)


def load_users() -> pd.DataFrame:
    """
    Load users from data/users.xlsx.
    Returns DataFrame with columns: name, pin, role, allowed_pages
    """
    # Try DB first (users table exists in DDL)
    try:
        if _db is not None:
            try:
                rows = _db.db_query('SELECT name, pin, role, allowed_pages FROM users ORDER BY id')
                if rows:
                    df = pd.DataFrame(rows)
                    df.columns = [c.strip().lower() for c in df.columns]
                    return df
            except Exception:
                pass
    except Exception:
        pass

    # Excel fallback
    ensure_users_file()
    try:
        df = pd.read_excel("data/users.xlsx")
        df.columns = [c.strip().lower() for c in df.columns]
        for col in ["name", "pin", "role", "allowed_pages"]:
            if col not in df.columns:
                df[col] = ""
        return df
    except Exception as e:
        print(f"Error loading users: {e}")
        return pd.DataFrame(columns=["name", "pin", "role", "allowed_pages"])


def save_users(df: pd.DataFrame):
    """
    Save users DataFrame to data/users.xlsx.
    """
    try:
        # Try DB upsert for each user row, then write Excel as fallback/persistence
        if _db is not None:
            try:
                for _, row in df.iterrows():
                    name = str(row.get('name') or '')
                    pin = str(row.get('pin') or '')
                    role = str(row.get('role') or '')
                    allowed = row.get('allowed_pages')
                    try:
                        existing = _db.db_query('SELECT id FROM users WHERE name = %s LIMIT 1', (name,))
                    except Exception:
                        existing = []
                    if existing:
                        try:
                            _db.db_execute('UPDATE users SET pin=%s, role=%s, allowed_pages=%s WHERE id = %s', (pin, role, str(allowed), existing[0].get('id')))
                        except Exception:
                            pass
                    else:
                        try:
                            _db.db_execute('INSERT INTO users(name, pin, role, allowed_pages) VALUES (%s,%s,%s,%s)', (name, pin, role, str(allowed)))
                        except Exception:
                            pass
            except Exception:
                pass

        os.makedirs("data", exist_ok=True)
        df.to_excel("data/users.xlsx", index=False)
    except Exception as e:
        print(f"Error saving users: {e}")


def validate_pin(pin: str) -> Optional[Dict]:
    """
    Validate PIN and return user record.
    
    Args:
        pin: 4-6 digit PIN string
    
    Returns:
        Dict with user data if valid, None otherwise
        Keys: name, pin, role, allowed_pages (list)
    """
    if not pin or len(pin) < 4:
        return None
    
    users = load_users()
    if users.empty:
        return None
    
    # Find user by PIN
    match = users[users["pin"].astype(str) == str(pin)]
    if match.empty:
        return None
    
    user_row = match.iloc[0]
    
    # Parse allowed_pages CSV to list
    pages_str = str(user_row.get("allowed_pages", ""))
    allowed = [p.strip() for p in pages_str.split(",") if p.strip()]
    
    return {
        "name": str(user_row.get("name", "Unknown")),
        "pin": str(user_row.get("pin", "")),
        "role": str(user_row.get("role", "viewer")),
        "allowed_pages": allowed
    }


def is_admin(user: Optional[Dict]) -> bool:
    """Check if user has admin role."""
    if not user:
        return False
    return user.get("role", "").lower() == "admin"


def can_access_page(user: Optional[Dict], page: str) -> bool:
    """
    Check if user can access a specific page.
    Admin bypasses all restrictions.
    """
    if not user:
        return False
    if is_admin(user):
        return True
    # Archive page is intended for admin/staff operational retrieval.
    if page == "archive" and user.get("role", "").lower() in {"admin", "staff"}:
        return True
    return page in user.get("allowed_pages", [])
