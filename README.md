# 离线部署：web-app-xd

新版本使用独立项目名、镜像名、容器名和端口，避免与服务器上已有的旧版本冲突。所有数据都存放在服务器 `/data/webxd` 下，不迁移旧数据。

## 1. 命名和端口

```text
项目名：web-app-xd
前端端口：8080 -> 容器 80
后端端口：8002 -> 容器 8000
数据库端口：不对外发布
```

镜像和容器：

```text
web-app-xd-frontend:1.0         -> web-app-xd-frontend
web-app-xd-backend:1.0          -> web-app-xd-backend
web-app-xd-asset-worker:1.0     -> web-app-xd-asset-worker
web-app-xd-quality-worker:1.0   -> web-app-xd-quality-worker
postgres:15                     -> web-app-xd-db
```

## 2. 服务器目录结构

```text
/data/webxd/
├── compose.server.yaml
├── .env
├── .env.example
├── server_load_and_start.sh
├── nginx/
│   └── nginx.conf
├── data/
│   ├── postgresql/
│   └── datasets/
├── flower-assets/
├── browse/
└── images/
    ├── web-app-xd-frontend-1.0.tar
    ├── web-app-xd-backend-1.0.tar
    ├── web-app-xd-asset-worker-1.0.tar
    ├── web-app-xd-quality-worker-1.0.tar
    └── postgres-15.tar
```

## 3. 在开发机打包镜像

```bash
cd /home/linux/Downloads/web-app-local-3.1
./deploy/scripts/build_offline_package.sh
```

执行后，镜像 tar 会生成在：

```text
deploy/images/
```

## 4. 把部署文件复制到服务器

将 `deploy/` 目录里的内容放到服务器的 `/data/webxd/` 下，注意不要把整个 `deploy` 文件夹作为子目录。

例如通过 scp：

```bash
cd /home/linux/Downloads/web-app-local-3.1
scp -r deploy/* user@服务器IP:/data/webxd/
```

如果服务器上没有 `/data/webxd`，先创建：

```bash
sudo mkdir -p /data/webxd
```

复制完成后，`/data/webxd/compose.server.yaml` 应该直接位于该目录下。

## 5. 在服务器上加载并启动

```bash
cd /data/webxd
sudo cp .env.example .env
sudo vi .env
```

至少修改：

```text
SECRET_KEY=请改为新的随机字符串
```

如果希望修改数据库密码，同时修改 `POSTGRES_PASSWORD`。

然后执行：

```bash
cd /data/webxd
sudo bash server_load_and_start.sh
```

脚本会：

1. 创建 `data/postgresql`、`data/datasets`、`flower-assets`、`browse` 等空目录。
2. 加载 `web-app-xd-*` 应用镜像。
3. 如果服务器已有 `postgres:15`，跳过加载，避免影响旧项目。
4. 使用 `docker compose -p web-app-xd -f compose.server.yaml up -d` 启动。

## 6. 手动加载和启动命令

如果不用脚本，手动执行：

```bash
cd /data/webxd

sudo docker load -i images/web-app-xd-frontend-1.0.tar
sudo docker load -i images/web-app-xd-backend-1.0.tar
sudo docker load -i images/web-app-xd-asset-worker-1.0.tar
sudo docker load -i images/web-app-xd-quality-worker-1.0.tar

if ! sudo docker image inspect postgres:15 >/dev/null 2>&1; then
  sudo docker load -i images/postgres-15.tar
fi

sudo docker compose -p web-app-xd -f compose.server.yaml up -d
sudo docker compose -p web-app-xd -f compose.server.yaml ps
```

## 7. 验证访问

```text
http://服务器IP:8080
```

后端直连：

```text
http://服务器IP:8002/docs
```

## 8. 注意

- 不迁移旧数据库、旧数据集和旧图像资产，首次启动会创建全新的空数据库和目录。
- 如需导入图像，先把待导入文件放入 `/data/webxd/browse/`，再在系统中进行图像资产导入。
- `postgres:15` 与旧项目共用镜像名是安全的，容器名和数据目录不同即可。
- 部署在隔离网运行时不需要下载 Python、Node、Nginx 或 PostgreSQL 依赖。

---

## structure main file into many folders
### postgresql zhparser && pgstattuple
- deepseek 对话



## 重新构建要在项目根目录下执行：

  /home/linux/Downloads/web-app-local-3.1

  因为 compose.build.yaml 里的 ./frontend 和 ./backend 是相对于这个根目录的。如果在 deploy/ 或其他目录执行，路径就会错。

  ## 1. 只修改了前端代码

  cd /home/linux/Downloads/web-app-local-3.1

  docker compose -f compose.build.yaml build frontend
  docker save -o deploy/images/web-app-xd-frontend-1.0.tar web-app-xd-frontend:1.0

  然后把这个新的 tar 复制到服务器 /data/webxd/images/，在服务器加载并重启：

  cd /data/webxd
  sudo docker load -i images/web-app-xd-frontend-1.0.tar
  sudo docker compose -p web-app-xd -f compose.server.yaml up -d frontend

  ## 2. 修改了后端代码

  后端代码被三个服务共用，但当前方案为它们分别构建了三个镜像名，所以需要重建：

  cd /home/linux/Downloads/web-app-local-3.1

  docker compose -f compose.build.yaml build backend asset-worker quality-worker

  docker save -o deploy/images/web-app-xd-backend-1.0.tar web-app-xd-backend:1.0
  docker save -o deploy/images/web-app-xd-asset-worker-1.0.tar web-app-xd-asset-worker:1.0
  docker save -o deploy/images/web-app-xd-quality-worker-1.0.tar web-app-xd-quality-worker:1.0

  服务器更新：

  cd /data/webxd

  sudo docker load -i images/web-app-xd-backend-1.0.tar
  sudo docker load -i images/web-app-xd-asset-worker-1.0.tar
  sudo docker load -i images/web-app-xd-quality-worker-1.0.tar

  sudo docker compose -p web-app-xd -f compose.server.yaml up -d backend asset-worker quality-worker

  ## 3. 前后端都修改了，直接全部重新构建并导出

  cd /home/linux/Downloads/web-app-local-3.1
  ./deploy/scripts/build_offline_package.sh

  这个脚本会：

  1. 在项目根目录执行构建。
  2. 重新导出全部镜像 tar，包括 postgres:15。
  3. 输出到 deploy/images/。

  然后还是把 deploy/images/ 里更新后的 tar 复制到服务器 /data/webxd/images/，在服务器执行：

  cd /data/webxd
  sudo bash server_load_and_start.sh

  或者手动加载后重启：

  cd /data/webxd

  sudo docker load -i images/web-app-xd-frontend-1.0.tar
  sudo docker load -i images/web-app-xd-backend-1.0.tar
  sudo docker load -i images/web-app-xd-asset-worker-1.0.tar
  sudo docker load -i images/web-app-xd-quality-worker-1.0.tar

  sudo docker compose -p web-app-xd -f compose.server.yaml up -d

  ## 注意

  - 构建一定是在有源码和 Docker 的开发机上做，不要在隔离服务器上执行 docker compose build。
  - 服务器只需要新的 tar 文件，加载后重启容器即可。
  - 如果只改了 deploy/nginx/nginx.conf，不需要重新构建镜像，只需要把这个配置文件复制到 /data/webxd/nginx/nginx.conf，然后重启前端
    容器：

  sudo docker compose -p web-app-xd -f compose.server.yaml restart frontend

### PostgreSQL zhparser 使用指南
- grok
- steps:
    - step1: superuser
    ``` cur.execute("""
                    CREATE EXTENSION IF NOT EXISTS zhparser;
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1 FROM pg_ts_config WHERE cfgname = 'chinese'
                        ) THEN
                            CREATE TEXT SEARCH CONFIGURATION chinese (PARSER = zhparser);
                            ALTER TEXT SEARCH CONFIGURATION chinese ADD MAPPING FOR n,v,a,i,d,l,j WITH simple;
                        END IF;
                    END
                    $$;
                """)
    ```

    - step2:  

    ``` GRANT USAGE ON SCHEMA public TO your_username; ```

    - step3: 连接到你的目标数据库，执行以下命令：
    ``` 
    \c your_database_name
    CREATE EXTENSION IF NOT EXISTS zhparser;
    CREATE TEXT SEARCH CONFIGURATION public.chinese (PARSER = zhparser);
    ALTER TEXT SEARCH CONFIGURATION public.chinese ADD MAPPING FOR n,v,a,i,d,e,l,j,u WITH simple; 
    ```



    - step4: 检查并重新创建中文搜索配置
    ``` cur.execute("""
            DO $$
            BEGIN
                -- 删除现有配置（如果需要重新创建）
                IF EXISTS (
                    SELECT 1 FROM pg_ts_config WHERE cfgname = 'chinese'
                ) THEN
                    -- 检查是否有依赖（tsvector 列）
                    PERFORM 1 FROM pg_attribute
                    WHERE atttypid = 'tsvector'::regtype
                    AND attrelid IN (
                        SELECT oid FROM pg_class
                        WHERE relnamespace = 'public'::regnamespace
                    );
                    IF FOUND THEN
                        -- 临时移除 markdown_documents 的 tsvector 列
                        ALTER TABLE markdown_documents DROP COLUMN IF EXISTS content_tsv;
                    END IF;
                    DROP TEXT SEARCH CONFIGURATION IF EXISTS chinese;
                END IF;

                -- 创建新配置
                CREATE TEXT SEARCH CONFIGURATION chinese (PARSER = zhparser);
                ALTER TEXT SEARCH CONFIGURATION chinese
                    ADD MAPPING FOR n,v,a,i,d,e,l,j,u WITH simple;
            END
            $$;
        """) 
    ```
