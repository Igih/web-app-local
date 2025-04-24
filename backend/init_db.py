import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from tenacity import retry, stop_after_attempt, wait_fixed
from config import DB_CONFIG
from services.auth import get_password_hash
import os
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
                # 创建 users 表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        password VARCHAR(255) NOT NULL,
                        role VARCHAR(10) NOT NULL DEFAULT 'user'
                    )
                """)
                # 创建 datasets 表
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
                # 创建 categories_show 表
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS categories_show (
                        id SERIAL PRIMARY KEY,
                        images TEXT[] NOT NULL,
                        description TEXT,
                        category VARCHAR(50) NOT NULL,
                        count INTEGER NOT NULL
                    )
                """)
                # 创建 markdown_documents 表，去掉 zhparser 相关配置
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS markdown_documents (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL REFERENCES users(id),
                        title VARCHAR(255) NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                # 创建触发器以更新 updated_at
                cur.execute("""
                    CREATE OR REPLACE FUNCTION update_timestamp() RETURNS TRIGGER AS $$
                    BEGIN
                        NEW.updated_at = CURRENT_TIMESTAMP;
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;

                    DROP TRIGGER IF EXISTS update_markdown_timestamp ON markdown_documents;
                    CREATE TRIGGER update_markdown_timestamp
                    BEFORE UPDATE ON markdown_documents
                    FOR EACH ROW EXECUTE FUNCTION update_timestamp();
                """)
                
                # 插入默认用户（从环境变量获取密码）
                default_users = [
                    ('root1', os.getenv('ROOT1_PASSWORD', 'root123'), 'admin'),
                    ('root2', os.getenv('ROOT2_PASSWORD', 'root123'), 'admin'),
                    # ('user', os.getenv('USER_PASSWORD', 'user123'), 'user'),
                    # ('testuser', os.getenv('TESTUSER_PASSWORD', 'user123'), 'user')
                ]
                for username, password, role in default_users:
                    hashed_password = get_password_hash(password)
                    cur.execute("""
                        INSERT INTO users (username, password, role)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (username) DO NOTHING
                    """, (username, hashed_password, role))
        logger.info("Database tables initialized")

    except psycopg2.OperationalError as e:
        logger.error(f"Database connection error: {str(e)}")
        raise
    except psycopg2.ProgrammingError as e:
        logger.error(f"SQL syntax error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

if __name__ == "__main__":
    init_db()