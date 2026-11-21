#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "==> 构建 xd 版本镜像"
docker compose -f compose.build.yaml build

mkdir -p deploy/images

if ! docker image inspect postgres:15 >/dev/null 2>&1; then
  echo "==> 本地缺少 postgres:15，先拉取"
  docker pull postgres:15
fi

echo "==> 导出离线镜像"
docker save -o deploy/images/web-app-xd-frontend-1.0.tar web-app-xd-frontend:1.0
docker save -o deploy/images/web-app-xd-backend-1.0.tar web-app-xd-backend:1.0
docker save -o deploy/images/web-app-xd-asset-worker-1.0.tar web-app-xd-asset-worker:1.0
docker save -o deploy/images/web-app-xd-quality-worker-1.0.tar web-app-xd-quality-worker:1.0
docker save -o deploy/images/postgres-15.tar postgres:15

echo "==> 离线包已生成到 deploy/images"
echo "请把 deploy/ 目录中的以下内容复制到服务器 /data/webxd/:"
echo "  compose.server.yaml"
echo "  .env.example"
echo "  nginx/nginx.conf"
echo "  images/*.tar"
echo "  server_load_and_start.sh"
