import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from config import DB_CONFIG  # 假设 DB_CONFIG 包含数据库连接参数

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('index_maintenance.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def check_index_status(conn):
    """检查 GIN 索引的大小和膨胀状态"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # 检查索引大小
            cur.execute("""
                SELECT pg_size_pretty(pg_relation_size('content_tsv_idx')) AS index_size
            """)
            index_size = cur.fetchone()['index_size']
            
            # 检查膨胀（需要 pgstattuple 扩展）
            cur.execute("""
                SELECT dead_tuple_percent
                FROM pgstattuple('content_tsv_idx')
            """)
            dead_tuple_percent = cur.fetchone()['dead_tuple_percent']
            
            logger.info(f"Index size: {index_size}, Dead tuple percent: {dead_tuple_percent}%")
            return {"index_size": index_size, "dead_tuple_percent": dead_tuple_percent}
    except Exception as e:
        logger.error(f"Error checking index status: {str(e)}")
        raise

def maintain_gin_index():
    """执行 GIN 索引维护：VACUUM ANALYZE 和 REINDEX CONCURRENTLY"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        status = {"success": False, "message": "", "index_status": {}}
        
        logger.info("Starting index maintenance...")
        
        # 检查索引状态（前）
        status["index_status"]["before"] = check_index_status(conn)
        
        with conn.cursor() as cur:
            # 运行 VACUUM ANALYZE
            logger.info("Running VACUUM ANALYZE on markdown_documents...")
            cur.execute("VACUUM ANALYZE markdown_documents;")
            
            # 运行 REINDEX CONCURRENTLY
            logger.info("Rebuilding GIN index (content_tsv_idx)...")
            cur.execute("REINDEX INDEX CONCURRENTLY content_tsv_idx;")
        
        # 检查索引状态（后）
        status["index_status"]["after"] = check_index_status(conn)
        
        logger.info("Index maintenance completed successfully.")
        status["success"] = True
        status["message"] = "Index maintenance completed."
        
        return status
    except Exception as e:
        logger.error(f"Error during index maintenance: {str(e)}")
        status["success"] = False
        status["message"] = f"Maintenance failed: {str(e)}"
        return status
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    result = maintain_gin_index()
    print(result)