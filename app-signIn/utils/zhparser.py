# 创建 zhparser 扩展  （need superuser）

# cur.execute("""
#     CREATE EXTENSION IF NOT EXISTS zhparser;
# """)

# 检查并重新创建中文搜索配置
# cur.execute("""
#     DO $$
#     BEGIN
#         -- 删除现有配置（如果需要重新创建）
#         IF EXISTS (
#             SELECT 1 FROM pg_ts_config WHERE cfgname = 'chinese'
#         ) THEN
#             -- 检查是否有依赖（tsvector 列）
#             PERFORM 1 FROM pg_attribute
#             WHERE atttypid = 'tsvector'::regtype
#             AND attrelid IN (
#                 SELECT oid FROM pg_class
#                 WHERE relnamespace = 'public'::regnamespace
#             );
#             IF FOUND THEN
#                 -- 临时移除 markdown_documents 的 tsvector 列
#                 ALTER TABLE markdown_documents DROP COLUMN IF EXISTS content_tsv;
#             END IF;
#             DROP TEXT SEARCH CONFIGURATION IF EXISTS chinese;
#         END IF;

#         -- 创建新配置
#         CREATE TEXT SEARCH CONFIGURATION chinese (PARSER = zhparser);
#         ALTER TEXT SEARCH CONFIGURATION chinese
#             ADD MAPPING FOR n,v,a,i,d,e,l,j,u WITH simple;
#     END
#     $$;
# """)