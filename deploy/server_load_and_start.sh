#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${WEBXD_BASE_DIR:-$SCRIPT_DIR}"

cd "$BASE_DIR"

echo "==> 创建数据目录"
mkdir -p \
  nginx \
  data/postgresql \
  data/datasets \
  flower-assets \
  browse \
  images

if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    echo "==> 已根据 .env.example 创建 .env，请检查并修改 SECRET_KEY"
  else
    echo "缺少 .env.example，将使用 Compose 默认值"
  fi
fi

echo "==> 加载应用镜像"
for tar_file in images/web-app-xd-*.tar; do
  [ -e "$tar_file" ] || continue
  echo "加载 $tar_file"
  docker load -i "$tar_file"
done

echo "==> 处理 postgres:15"
if docker image inspect postgres:15 >/dev/null 2>&1; then
  echo "postgres:15 已存在，跳过加载，避免影响旧项目"
else
  docker load -i images/postgres-15.tar
fi

echo "==> 启动 web-app-xd"
docker compose -p web-app-xd -f compose.server.yaml up -d

echo "==> 当前容器状态"
docker compose -p web-app-xd -f compose.server.yaml ps
