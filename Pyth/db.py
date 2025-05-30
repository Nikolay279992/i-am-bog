import sqlite3
from datetime import datetime, timedelta

DB_NAME = "db.sqlite"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            expires_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def set_subscription_active(user_id: int, days: int):
    expires_at = (datetime.now() + timedelta(days=days)).isoformat()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        REPLACE INTO subscriptions (user_id, expires_at)
        VALUES (?, ?)
    ''', (user_id, expires_at))
    conn.commit()
    conn.close()

def is_subscription_active(user_id: int) -> bool:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT expires_at FROM subscriptions WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        expires_at = datetime.fromisoformat(row[0])
        return expires_at > datetime.now()
    return False

def get_subscription_expiry(user_id: int) -> str | None:
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT expires_at FROM subscriptions WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None