# # 创建 zhparser 扩展  （need superuser）

# step1: cur.execute("""
#                     CREATE EXTENSION IF NOT EXISTS zhparser;
#                     DO $$
#                     BEGIN
#                         IF NOT EXISTS (
#                             SELECT 1 FROM pg_ts_config WHERE cfgname = 'chinese'
#                         ) THEN
#                             CREATE TEXT SEARCH CONFIGURATION chinese (PARSER = zhparser);
#                             ALTER TEXT SEARCH CONFIGURATION chinese ADD MAPPING FOR n,v,a,i,d,l,j WITH simple;
#                         END IF;
#                     END
#                     $$;
#                 """)

# step2: GRANT USAGE ON SCHEMA public TO your_username;

# step3: 连接到你的目标数据库，执行以下命令：
# \c your_database_name
# CREATE EXTENSION IF NOT EXISTS zhparser;
# CREATE TEXT SEARCH CONFIGURATION public.chinese (PARSER = zhparser);
# ALTER TEXT SEARCH CONFIGURATION public.chinese ADD MAPPING FOR n,v,a,i,d,e,l,j,u WITH simple;



# step4: 检查并重新创建中文搜索配置
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