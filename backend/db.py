import os, json
try:
    import psycopg2
    import psycopg2.pool
    HAS_PSYCOPG2 = True
except ImportError:
    HAS_PSYCOPG2 = False

DATABASE_URL = os.environ.get("DATABASE_URL", "")

_pool = None

def get_pool():
    global _pool
    if _pool is None and DATABASE_URL and HAS_PSYCOPG2:
        _pool = psycopg2.pool.ThreadedConnectionPool(minconn=1, maxconn=10, dsn=DATABASE_URL)
    return _pool

def get_conn():
    pool = get_pool()
    if pool:
        return pool.getconn()
    return None

def put_conn(conn):
    pool = get_pool()
    if pool and conn:
        pool.putconn(conn)

def init_db():
    if not DATABASE_URL or not HAS_PSYCOPG2 or not DATABASE_URL.startswith("postgresql"):
        return False
    conn = get_conn()
    if not conn:
        return False
    try:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id SERIAL PRIMARY KEY,
                user_name TEXT NOT NULL,
                tickers TEXT NOT NULL,
                weights TEXT NOT NULL,
                result TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        return True
    except Exception as e:
        print(f"  DB init failed: {e}")
        return False
    finally:
        put_conn(conn)

def save_history(user_name, tickers, weights, result):
    if not DATABASE_URL or not HAS_PSYCOPG2 or not DATABASE_URL.startswith("postgresql"):
        return
    conn = get_conn()
    if not conn:
        return
    try:
        c = conn.cursor()
        c.execute(
            "INSERT INTO history (user_name, tickers, weights, result) VALUES (%s, %s, %s, %s)",
            (user_name, json.dumps(tickers), json.dumps(weights), json.dumps(result))
        )
        conn.commit()
    except Exception as e:
        print(f"  DB save failed: {e}")
    finally:
        put_conn(conn)

def get_history(user_name):
    if not DATABASE_URL or not HAS_PSYCOPG2 or not DATABASE_URL.startswith("postgresql"):
        return []
    conn = get_conn()
    if not conn:
        return []
    try:
        c = conn.cursor()
        c.execute(
            "SELECT id, tickers, weights, result, created_at FROM history WHERE user_name = %s ORDER BY created_at DESC",
            (user_name,)
        )
        rows = c.fetchall()
        return [
            {
                "id": r[0],
                "tickers": json.loads(r[1]),
                "weights": json.loads(r[2]),
                "result": json.loads(r[3]),
                "created_at": r[4].isoformat() if hasattr(r[4], 'isoformat') else r[4],
            }
            for r in rows
        ]
    except Exception as e:
        print(f"  DB query failed: {e}")
        return []
    finally:
        put_conn(conn)
