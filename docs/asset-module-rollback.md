# 图像资源管理模块回滚方案

## 适用范围

本模块仅新增 `asset` Schema、`asset_*` 后端文件、`frontend/src/views/assets/` 页面，以及少量路由和菜单改动。旧 `public` 表、旧 API、旧菜单均未被替换。

## 回滚步骤

1. 停止涉及资产模块的服务：

   ```bash
   docker compose stop asset-worker backend frontend
   ```

2. 回滚数据库迁移：

   ```bash
   cd backend
   alembic downgrade -1
   ```

   如需回滚到迁移前：

   ```bash
   alembic downgrade base
   ```

3. 如确认不需要资产文件，备份后清理宿主机目录：

   ```bash
   sudo mv /srv/flower-assets /srv/flower-assets.backup.$(date +%Y%m%d%H%M%S)
   ```

4. 回滚代码：

   ```bash
   git revert <asset-module-commits>
   ```

5. 重新启动旧业务：

   ```bash
   docker compose up -d db frontend backend
   ```

## 数据恢复

如果已经备份过 PostgreSQL 和资产目录，按以下顺序恢复：

1. 恢复 PostgreSQL 备份。
2. 恢复 `/srv/flower-assets`。
3. 执行 `alembic upgrade head`。
4. 启动全部服务。

## 注意事项

- 迁移使用 `DROP SCHEMA IF EXISTS asset CASCADE`，只会删除 `asset` Schema，不会触碰 `public` 旧表。
- 代码回滚后，`compose.yaml` 中 `asset-worker` 服务和资产挂载可保留，也可一并删除；保留不会影响旧业务。
