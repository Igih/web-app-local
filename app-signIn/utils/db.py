import psycopg2
from psycopg2.pool import SimpleConnectionPool
from psycopg2.extras import RealDictCursor
from tenacity import retry, stop_after_attempt, wait_fixed

from contextlib import contextmanager
import logging
from config import DB_CONFIG

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

DB_POOL = None

def init_db_pool():
    global DB_POOL
    try:
        DB_POOL = SimpleConnectionPool(minconn=1, maxconn=20, **DB_CONFIG)
        logger.info("Connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {str(e)}")
        raise

@retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
def get_db_connection():
    return DB_POOL.getconn()

def get_db_cursor(conn):
    return conn.cursor(cursor_factory=RealDictCursor)

def release_db_connection(conn):
    try:
        if conn and not conn.closed:
            conn.rollback()
    except Exception as e:
        logger.warning(f"Error rolling back connection: {str(e)}")
    finally:
        if conn:
            DB_POOL.putconn(conn)
            logger.debug("Connection released to pool")

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
        release_db_connection(conn)

@contextmanager
def db_connection():
    conn = get_db_connection()
    try:
        yield conn
    finally:
        release_db_connection(conn)