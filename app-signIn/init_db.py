import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
from config import DB_CONFIG
from services.auth import get_password_hash

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

@contextmanager
def db_transaction():
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

@retry(stop=stop_after_attempt(5), wait=wait_fixed(2))
def init_db():
    try:
        with db_transaction() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password VARCHAR(100) NOT NULL,
                        role VARCHAR(10) NOT NULL DEFAULT 'user'
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS datasets (
                        id SERIAL PRIMARY KEY,
                        filename VARCHAR(255) NOT NULL,
                        uploader_type VARCHAR(10) NOT NULL,
                        uploader_id INTEGER REFERENCES users(id),
                        category VARCHAR(50) NOT NULL,
                        description TEXT,
                        size BIGINT NOT NULL,
                        path VARCHAR(512) NOT NULL,
                        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS categories_show (
                        id SERIAL PRIMARY KEY,
                        images TEXT[] NOT NULL,
                        description TEXT,
                        category VARCHAR(50) NOT NULL,
                        count INTEGER NOT NULL
                    )
                """)
                hashed_password = get_password_hash("root123")
                cur.execute("""
                    INSERT INTO users (username, password, role)
                    VALUES ('root1', %s, 'admin')
                    ON CONFLICT (username) DO NOTHING
                """, (hashed_password,))
                hashed_password = get_password_hash("root123")
                cur.execute("""
                    INSERT INTO users (username, password, role)
                    VALUES ('root2', %s, 'admin')
                    ON CONFLICT (username) DO NOTHING
                """, (hashed_password,))
                hashed_password = get_password_hash("user123")
                cur.execute("""
                    INSERT INTO users (username, password, role)
                    VALUES ('user', %s, 'admin')
                    ON CONFLICT (username) DO NOTHING
                """, (hashed_password,))
        logger.info("Database tables initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

if __name__ == "__main__":
    init_db()