"""
SolSniperX Database Utility Module
SQLite database for trades, positions, limit orders, and system stats.
Merged from SolSniperX v3.3.0 (Ultimate Intelligence Upgrade) branch.
"""

import sqlite3
import os
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database', 'app.db')

def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency support
    return conn

def init_db():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create trades table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_address TEXT NOT NULL,
        token_symbol TEXT,
        type TEXT NOT NULL, -- 'buy' or 'sell'
        amount_sol REAL,
        amount_tokens REAL,
        price_usd REAL,
        transaction_id TEXT UNIQUE,
        status TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # Create active positions table for AutoTrader
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS positions (
        token_address TEXT PRIMARY KEY,
        token_symbol TEXT,
        buy_price REAL NOT NULL,
        highest_price REAL,
        amount_tokens REAL NOT NULL,
        buy_amount_sol REAL,
        purchase_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        metadata TEXT -- JSON string for additional state like hit TP tiers
    )
    ''')

    # Migration for existing databases
    try:
        cursor.execute('ALTER TABLE positions ADD COLUMN metadata TEXT')
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Create system_stats table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS system_stats (
        key TEXT PRIMARY KEY,
        value INTEGER DEFAULT 0
    )
    ''')

    # Initialize rugs_avoided if not exists
    cursor.execute('INSERT OR IGNORE INTO system_stats (key, value) VALUES ("rugs_avoided", 0)')

    # Create limit_orders table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS limit_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token_address TEXT NOT NULL,
        token_symbol TEXT,
        target_price REAL NOT NULL,
        amount_sol REAL NOT NULL,
        side TEXT NOT NULL, -- 'buy' or 'sell'
        status TEXT DEFAULT 'pending', -- 'pending', 'executed', 'cancelled'
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    conn.commit()
    conn.close()

def record_trade(trade_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO trades (token_address, token_symbol, type, amount_sol, amount_tokens, price_usd, transaction_id, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade_data.get('token_address'),
            trade_data.get('token_symbol'),
            trade_data.get('type'),
            trade_data.get('amount_sol'),
            trade_data.get('amount_tokens'),
            trade_data.get('price_usd'),
            trade_data.get('transaction_id'),
            trade_data.get('status'),
            trade_data.get('timestamp', datetime.now().isoformat())
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Already exists
    except Exception as e:
        logger.error(f"Error recording trade: {e}")
    finally:
        conn.close()

def save_position(position_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        metadata_json = json.dumps(position_data.get('metadata', {}))
        cursor.execute('''
        INSERT OR REPLACE INTO positions (token_address, token_symbol, buy_price, highest_price, amount_tokens, buy_amount_sol, purchase_time, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            position_data['token_address'],
            position_data.get('token_symbol'),
            position_data['buy_price'],
            position_data.get('highest_price', position_data['buy_price']),
            position_data['amount_tokens'],
            position_data.get('buy_amount_sol'),
            position_data.get('purchase_time', datetime.now().isoformat()),
            metadata_json
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving position: {e}")
    finally:
        conn.close()

def remove_position(token_address):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('DELETE FROM positions WHERE token_address = ?', (token_address,))
        conn.commit()
    except Exception as e:
        logger.error(f"Error removing position: {e}")
    finally:
        conn.close()

def get_active_positions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM positions')
    rows = cursor.fetchall()
    positions = []
    for row in rows:
        pos = dict(row)
        if pos.get('metadata'):
            try:
                pos['metadata'] = json.loads(pos['metadata'])
            except Exception:
                pos['metadata'] = {}
        else:
            pos['metadata'] = {}
        positions.append(pos)
    conn.close()
    return positions

def get_recent_trades(limit=50):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?', (limit,))
    trades = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return trades

def get_trade_stats():
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT COUNT(*) FROM trades WHERE type = "buy" AND status = "confirmed"')
        total_buys = cursor.fetchone()[0]

        cursor.execute('SELECT COUNT(*) FROM trades WHERE type = "sell" AND status = "confirmed"')
        total_sells = cursor.fetchone()[0]

        # Calculate total profit
        cursor.execute('SELECT SUM(amount_sol) FROM trades WHERE type = "sell" AND status = "confirmed"')
        total_sell_sol = cursor.fetchone()[0] or 0.0

        cursor.execute('SELECT SUM(amount_sol) FROM trades WHERE type = "buy" AND status = "confirmed"')
        total_buy_sol = cursor.fetchone()[0] or 0.0

        total_profit_sol = total_sell_sol - total_buy_sol

        # Calculate success rate
        cursor.execute('''
            SELECT token_address, SUM(CASE WHEN type = 'sell' THEN amount_sol ELSE -amount_sol END) as pnl
            FROM trades
            WHERE status = 'confirmed'
            GROUP BY token_address
            HAVING SUM(CASE WHEN type = 'sell' THEN 1 ELSE 0 END) > 0
        ''')

        token_pnls = cursor.fetchall()
        profitable_tokens_count = sum(1 for row in token_pnls if row['pnl'] > 0)
        total_traded_tokens_count = len(token_pnls)

        success_rate = 0.0
        if total_traded_tokens_count > 0:
            success_rate = (profitable_tokens_count / total_traded_tokens_count) * 100

        # Get rugs avoided
        rugs_avoided = get_rugs_avoided()

        return {
            "totalProfit": round(total_profit_sol, 4),
            "totalTrades": total_buys + total_sells,
            "totalBuys": total_buys,
            "totalSells": total_sells,
            "successRate": round(success_rate, 2),
            "rugsAvoided": rugs_avoided
        }
    except Exception as e:
        logger.error(f"Error getting trade stats: {e}")
        return {"totalProfit": 0, "totalTrades": 0, "successRate": 0, "rugsAvoided": 0}
    finally:
        conn.close()

def increment_rugs_avoided():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE system_stats SET value = value + 1 WHERE key = "rugs_avoided"')
        conn.commit()
    except Exception as e:
        logger.error(f"Error incrementing rugs avoided: {e}")
    finally:
        conn.close()

def get_rugs_avoided():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT value FROM system_stats WHERE key = "rugs_avoided"')
        row = cursor.fetchone()
        return row[0] if row else 0
    except Exception as e:
        logger.error(f"Error getting rugs avoided: {e}")
        return 0
    finally:
        conn.close()

def save_limit_order(order_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO limit_orders (token_address, token_symbol, target_price, amount_sol, side, status)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            order_data['token_address'],
            order_data.get('token_symbol'),
            order_data['target_price'],
            order_data['amount_sol'],
            order_data['side'],
            order_data.get('status', 'pending')
        ))
        conn.commit()
    except Exception as e:
        logger.error(f"Error saving limit order: {e}")
    finally:
        conn.close()

def get_pending_limit_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM limit_orders WHERE status = "pending"')
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return orders

def update_limit_order_status(order_id, status):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE limit_orders SET status = ? WHERE id = ?', (status, order_id))
        conn.commit()
    except Exception as e:
        logger.error(f"Error updating limit order status: {e}")
    finally:
        conn.close()
