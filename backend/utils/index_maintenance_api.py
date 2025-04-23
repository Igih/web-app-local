from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from config import DB_CONFIG
from services.auth import get_current_user  # 假设已实现 JWT 认证

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

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")  # 假设 token 端点已定义

def check_index_status(conn):
    """检查 GIN 索引的大小和膨胀状态"""
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT pg_size_pretty(pg_relation_size('content_tsv_idx')) AS index_size
            """)
            index_size = cur.fetchone()['index_size']
            
            cur.execute("""
                SELECT dead_tuple_percent
                FROM pgstattuple('content_tsv_idx')
            """)
            dead_tuple_percent = cur.fetchone()['dead_tuple_percent']
            
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
        
        logger.info("Starting index maintenance via API...")
        
        # 检查索引状态（前）
        status["index_status"]["before"] = check_index_status(conn)
        
        with conn.cursor() as cur:
            logger.info("Running VACUUM ANALYZE on markdown_documents...")
            cur.execute("VACUUM ANALYZE markdown_documents;")
            
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

@app.post("/admin/maintain-index", response_model=dict)
async def trigger_index_maintenance(current_user: dict = Depends(get_current_user)):
    """
    管理员端点：触发 GIN 索引维护
    """
    # 检查用户角色
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can perform index maintenance"
        )
    
    # 执行维护
    result = maintain_gin_index()
    
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["message"]
        )
    
    return result