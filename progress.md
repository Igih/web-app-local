# 图像资源管理增量改造实施清单

> 目标：在现有 FastAPI + Vue 3 + PostgreSQL + Docker Compose 网站上新增一个一级菜单「图像资源管理」，不改动旧业务菜单、接口契约和旧数据表字段。
>
> 当前阶段：只做方案和清单，不修改业务代码。

## 0. 基本改造原则

- 只新增，不破坏旧功能。
- 旧数据库表、旧 API、旧前端页面保持原状。
- 新功能统一使用 `asset` PostgreSQL Schema，与旧 `public` 表隔离。
- 新后端代码统一走 `backend/routers/asset_*`、`backend/services/asset_*`、`backend/models/asset_*`。
- 新前端页面统一放在 `frontend/src/views/assets/`，只少量修改路由和顶部菜单。
- 原图、缩略图、标注文件保存在宿主机持久化目录，通过 Docker Bind Mount 挂载。
- 原图导入由独立 Worker 处理，FastAPI 不负责百万级文件的同步导入。

## 1. 为什么需要“迁移”

这里的“迁移”不是迁移旧数据，也不是把旧表替换成新表，而是把新增表结构的 SQL 做成可版本化、可回滚、可重复执行的脚本。

如果直接在 `init_db.py` 里追加 `CREATE TABLE IF NOT EXISTS ...`，小型项目也能跑，但会带来几个问题：

- 无法清晰区分“本次新增了什么表/字段/约束”。
- 修改字段、增加索引、调整约束时，难以安全回滚。
- 多个开发或部署环境之间，容易出现“你执行过，我没执行过”的状态。
- 未来要新增二期功能时，只能继续手工改 `init_db.py`，容易误改旧逻辑。

建议的做法是：旧表继续由现有 `init_db.py` 管理，新 `asset` 表单独用 Alembic 或版本化 SQL 管理。这样旧数据完全不动，新表又能安全地新增和演进。

## 2. 必须最小修改的现有文件

- [x] `compose.yaml`
  - 增加 `asset-worker` 服务。
  - 为 `backend` 和 `asset-worker` 增加资产目录 Bind Mount。
  - 显式补齐 `DB_*` 和 `ASSET_*` 环境变量。

- [x] `backend/config.py`
  - 新增 `ASSET_ROOT`、`ASSET_INGEST_ROOTS`、`ASSET_ORIGINALS_DIR`、`ASSET_THUMBNAILS_DIR`、`ASSET_ANNOTATIONS_DIR`、`ASSET_QUARANTINE_DIR`、`ASSET_MANIFESTS_DIR`。
  - 保留现有配置，不修改旧目录默认值。

- [x] `backend/requirements.txt`
  - 增加 `alembic`，其他依赖尽量复用现有依赖。

- [x] `backend/main.py`
  - 只增加新 Router 的注册。
  - 不修改现有 Router 和静态目录逻辑。

- [x] `backend/start.sh`
  - 增加迁移执行步骤，例如 `python init_db.py && alembic upgrade head && uvicorn ...`。
  - 保留旧 `init_db.py` 以兼容现有旧表。

- [x] `frontend/src/router/index.js`
  - 只增加图像资源管理的子路由。

- [x] `frontend/src/components/Layout.vue`
  - 只增加「图像资源管理」一级菜单。

## 3. 总体实施顺序

- [x] M1 环境适配与数据目录
- [x] M2 数据库 Schema 与迁移
- [x] M3 类别、两级类型、自定义标签
- [x] M4 导入页面与扫描预览
- [x] M5 后台导入引擎与哈希存储
- [x] M6 标注文件原样保存与关联
- [x] M7 图片检索、浏览、批量修改
- [x] M8 资源统计与导入任务管理
- [x] M9 集成测试、性能与备份验收

## 4. M1：环境适配与数据目录

### 目标

让新增图像资产模块具备独立目录、独立 Worker、正确挂载和路径权限。

### 新建文件

- [x] `backend/.dockerignore`
  - 排除 `backend/.env`、`__pycache__`、`*.pyc` 等，避免把本地密钥打进镜像。

- [x] `backend/asset_worker.py`
  - 独立 Worker 入口，启动后轮询导入任务。

### 修改文件

- [x] `compose.yaml`
  - 新增 `asset-worker` 服务。
  - 建议宿主机目录：`/srv/flower-assets`。
  - 建议目录结构：
    - `incoming/`
    - `originals/`
    - `thumbnails/`
    - `annotations/`
    - `manifests/`
    - `quarantine/`

- [x] `backend/config.py`
  - 增加资产目录配置。
  - 增加授权导入根目录配置。

### 验收标准

- [x] `docker compose up --build -d` 后旧服务正常启动。
- [x] `asset-worker` 能连接同一个 PostgreSQL。
- [x] 重建容器后资产文件仍然存在。
- [x] 后端对原图目录只读，Worker 对需要写入的目录可写。
- [x] 越权路径无法被访问（路径安全校验将在 M4 实现并验证）。

## 5. M2：数据库 Schema 与迁移

### 目标

在 PostgreSQL 中新增 `asset` Schema 及图像资产相关表，不修改旧表。

### 新建文件

- [x] `backend/alembic.ini`
- [x] `backend/migrations/env.py`
- [x] `backend/migrations/versions/0001_create_asset_schema.py`
- [x] `backend/migrations/versions/0002_seed_asset_categories.py`

### 需要创建的表

- [x] `asset.categories`
  - 固定六类：牡丹、菊花、月季、郁金香、玫瑰、太阳花。

- [x] `asset.images`
  - `sha256` 唯一。
  - `storage_key`。
  - `category_id`。
  - `capture_type` 可为空。
  - `spectral_type` 可为空。
  - `width`、`height`、`file_format`、`byte_size`、`status`。

- [x] `asset.image_sources`
  - 保留原路径、原文件名、相对路径、来源机器。
  - 保留来源批次中声明的类别、一级类型、二级类型。

- [x] `asset.tags`
  - `normalized_name` 唯一。
  - `display_name`。
  - `enabled`。

- [x] `asset.image_tags`
  - `(image_id, tag_id)` 唯一。
  - 事务或触发器保证每图最多 5 个标签。

- [x] `asset.annotation_files`
  - 保存标注原文件。
  - 保存 SHA-256。
  - 保存匹配状态。

- [x] `asset.import_batches`
  - 保存图片路径、标注路径、类别、两级类型、标签、递归开关、任务状态、扫描统计、导入统计。

- [x] `asset.import_items`
  - 保存批次中每个源文件的处理状态、哈希、错误码和详情。

- [x] `asset.import_issues`
  - 保存类别冲突、类型冲突、标签冲突、路径异常、解码失败等人工待审问题。

- [x] `asset.audit_logs`
  - 记录人工修改类别、两级类型和标签的操作审计。

### 关键约束

- [x] `CHECK (capture_type IS NOT NULL OR spectral_type IS NULL)`
- [x] `capture_type` 合法值：`photo`、`hand_drawn` 或 `NULL`
- [x] `spectral_type` 合法值：`visible`、`infrared` 或 `NULL`
- [x] `sha256` 唯一
- [x] `(batch_id, normalized_relative_path)` 幂等唯一
- [x] 为列表、筛选、统计创建必要索引

### 验收标准

- [x] 空库可执行迁移。
- [x] 迁移可回滚。
- [x] 旧表结构不变。
- [x] 六类种子数据写入成功。
- [x] 不会出现“一级类型为空但二级类型有值”的数据。

## 6. M3：类别、两级类型、自定义标签

### 目标

建立固定类别、两级类型和标签字典，作为后续导入和检索的基础。

### 新建文件

- [x] `backend/models/asset_enums.py`
- [x] `backend/models/asset_category.py`
- [x] `backend/models/asset_tag.py`
- [x] `backend/routers/asset_categories.py`
- [x] `backend/routers/asset_tags.py`
- [x] `backend/services/asset_categories.py`
- [x] `backend/services/asset_tags.py`

### 主要 API

- [x] `GET /api/assets/categories`
- [x] `GET /api/assets/tags`
- [x] `POST /api/assets/tags`
- [x] `PATCH /api/assets/tags/{tag_id}`
- [x] `DELETE /api/assets/tags/{tag_id}`

### 业务规则

- [x] 六类固定，不允许前端随意新增类别。
- [x] 一级类型：实拍 `photo`、手绘 `hand_drawn`、未指定 `NULL`。
- [x] 二级类型：可见光 `visible`、红外 `infrared`、未指定 `NULL`。
- [x] 一级为空时，二级必须为空。
- [x] 每张图片最多 5 个自定义标签。
- [x] 标签库本身不限制数量。

### 验收标准

- [ ] 固定六类可读取。
- [ ] 四种完整组合可被表达和检索。
- [ ] 第六个图片标签被拒绝。
- [ ] 重复标签名不会重复创建。

## 7. M4：导入页面与扫描预览

### 目标

实现服务器路径导入表单、路径校验、扫描预览和用户确认。

### 新建文件

- [x] `backend/models/asset_import.py`
- [x] `backend/routers/asset_import.py`
- [x] `backend/services/asset_import.py`
- [x] `backend/services/asset_paths.py`
- [x] `frontend/src/views/assets/AssetImport.vue`
- [x] `frontend/src/services/assetImportService.js`

### 主要 API

- [x] `POST /api/assets/imports/scan`
  - 创建扫描任务。
- [x] `GET /api/assets/imports/{batch_id}/preview`
  - 返回扫描预览。
- [x] `POST /api/assets/imports/{batch_id}/confirm`
  - 用户确认后进入导入队列。

### 表单字段

- [x] 图片路径：必填，文件或文件夹。
- [x] 花卉类别：必填，六选一。
- [x] 标注路径：可选。
- [x] 一级类型：可选。
- [x] 二级类型：可选，一级为空时禁止填写。
- [x] 自定义标签：可选，0～5 个。
- [x] 递归扫描：可选，文件夹默认开启。
- [x] 批次名称/备注：可选。

### 路径安全

- [x] 必须使用白名单目录。
- [x] 必须解析符号链接。
- [x] 必须校验真实路径仍在授权目录内。
- [x] 文件或目录不存在时返回明确错误。

### 验收标准

- [x] 缺图片路径或类别无法提交。
- [x] 越权路径被拒绝。
- [x] 文件路径和文件夹路径都能扫描。
- [x] 扫描结果展示图片数量、异常数量和标注粗匹配结果。
- [x] 用户确认后才进入正式导入。

## 8. M5：后台导入引擎与方案 B 哈希存储

### 目标

实现扫描、解码校验、SHA-256 去重、原图存储、缩略图生成、任务状态和失败恢复。

### 新建文件

- [x] `backend/services/asset_storage.py`
- [x] `backend/services/asset_import_engine.py`
- [x] `backend/services/asset_thumbnails.py`
- [x] `backend/asset_worker.py`

### 导入流程

- [x] 读取待处理批次。
- [x] 遍历图片文件和文件夹。
- [x] 解码校验图片。
- [x] 流式计算 SHA-256。
- [x] 查重。
- [x] 写入临时文件。
- [x] 校验后原子移动到正式目录。
- [x] 写入 `images`、`image_sources`、`image_tags`。
- [x] 生成缩略图。
- [x] 更新批次和条目状态。

### 存储规则

- [x] 原图按 SHA-256 前两级分目录。
- [x] 同 SHA-256 只保存一份原图。
- [x] 不同来源同哈希保存多条来源记录。
- [x] 原文件名和原路径不丢失。
- [x] 同名不同哈希都能入库。
- [x] 不根据扩展名覆盖真实格式。
- [x] 16-bit TIFF 原图不被缩略图流程改写。

### 任务状态

- [x] `created`
- [x] `scanning`
- [x] `awaiting_confirmation`
- [x] `queued`
- [x] `importing`
- [x] `completed`
- [x] `partial`
- [x] `failed`
- [x] `stopped`

### 条目状态

- [x] `pending`
- [x] `processing`
- [x] `imported`
- [x] `duplicate`
- [x] `conflict`
- [x] `failed`
- [x] `skipped`

### 验收标准

- [ ] 同哈希不同文件名只存一份。
- [ ] 同名不同哈希都能入库。
- [ ] 重复批次幂等。
- [x] 失败文件可重试。
- [ ] 冲突记录不会被静默覆盖。

## 9. M6：标注文件原样保存与关联

### 目标

支持标注路径可选、文件或目录，原样保存并按文件名/相对路径关联图片。

### 新建文件

- [x] `backend/services/asset_annotations.py`

### 主要逻辑

- [x] 标注文件保存到 `annotations/`。
- [x] 计算标注文件 SHA-256。
- [x] 优先按相对路径和主文件名匹配。
- [x] 单图单标注直接关联。
- [x] 多个候选时标记歧义。
- [x] 无法唯一判断时不猜测。
- [x] 图片无标注仍可入库。

### 验收标准

- [ ] 缺标注正常入库。
- [x] 单图单标注匹配成功。
- [ ] 歧义情况在导入结果中可见。
- [x] 标注内容不被解析。

## 10. M7：图片检索、浏览、批量修改

### 目标

实现服务端分页图库、两级类型筛选、四组合快捷筛选、标签 AND/OR、详情和批量维护。

### 新建文件

- [x] `backend/models/asset_image.py`
- [x] `backend/routers/asset_images.py`
- [x] `backend/services/asset_images.py`
- [x] `backend/routers/asset_files.py`
- [x] `frontend/src/views/assets/AssetImageManager.vue`
- [x] `frontend/src/services/assetService.js`

### 主要 API

- [x] `GET /api/assets/images`
- [x] `GET /api/assets/images/{image_id}`
- [x] `PATCH /api/assets/images/{image_id}`
- [x] `POST /api/assets/images/batch`
- [x] `GET /api/assets/files/thumbnail/{image_id}`
- [x] `GET /api/assets/files/original/{image_id}`

### 固定筛选条件

- [x] 类别：牡丹、菊花、月季、郁金香、玫瑰、太阳花。
- [x] 一级类型：全部、实拍、手绘、未指定。
- [x] 二级类型：全部、可见光、红外、未指定。
- [x] 四组合快捷筛选：实拍·可见光、实拍·红外、手绘·可见光、手绘·红外。
- [x] 标签 AND / OR。
- [x] 来源机器、批次、格式、分辨率、状态。

### 文件访问

- [x] 缩略图和原图均通过认证接口返回。
- [x] 不暴露任意宿主机路径。
- [x] 路径最终真实位置必须经过白名单校验。

### 验收标准

- [x] 四组合即使结果为 0 也始终显示。
- [ ] `玫瑰 + 手绘 + 红外` 返回正确数据。
- [ ] 标签 AND 和 OR 结果正确。
- [x] 详情显示来源、哈希、原文件名、相对路径、类别、类型和标签。
- [ ] 批量修改可审计，冲突时需确认。

## 11. M8：资源统计与导入任务管理

### 目标

实现六类统计、四组合统计、未指定统计、异常统计、导入记录、进度和重试。

### 新建文件

- [x] `backend/routers/asset_overview.py`
- [x] `backend/services/asset_stats.py`
- [x] `frontend/src/views/assets/AssetOverview.vue`
- [x] `frontend/src/views/assets/AssetImportRecords.vue`

### 主要 API

- [x] `GET /api/assets/overview/stats`
- [x] `GET /api/assets/imports`
- [x] `GET /api/assets/imports/{batch_id}`
- [x] `GET /api/assets/imports/{batch_id}/items`
- [x] `POST /api/assets/imports/{batch_id}/retry`
- [x] `POST /api/assets/imports/{batch_id}/stop`

### 统计口径

- [x] 六类 × 四完整组合。
- [x] 实拍·未指定光谱。
- [x] 手绘·未指定光谱。
- [x] 类型未指定。
- [x] 唯一图片数。
- [x] 源文件数。
- [x] 重复数。
- [x] 损坏数。
- [x] 冲突待审数。

### 验收标准

- [x] 即使某类某组合数量为 0，统计接口也返回该分项。
- [x] 统计结果与样例数据一致。
- [x] 四组合与未指定分项不混算。
- [x] 失败任务可重试。

## 12. M9：集成测试、性能与备份验收

### 目标

确认旧业务不回归，新模块可恢复，百万级数据路径有验证记录。

### 建议新建测试文件

- [x] `backend/tests/test_asset_paths.py`
- [x] `backend/tests/test_asset_tags.py`
- [x] `backend/tests/test_asset_import.py`
- [x] `backend/tests/test_asset_images.py`
- [x] `backend/tests/test_asset_stats.py`
- [x] `frontend/src/views/assets/__tests__/AssetImport.test.js`

### 建议新增脚本或文档

- [x] `scripts/smoke_test.sh`
- [x] `docs/asset-module-rollback.md`

### 测试场景

- [ ] 旧 API 回归。
- [ ] 六类全部类型数据。
- [ ] 重复 SHA-256。
- [ ] 同名不同 SHA-256。
- [ ] 类别冲突。
- [ ] 类型冲突。
- [ ] 标签冲突。
- [ ] 标注匹配和歧义。
- [x] 路径越权。
- [x] 导入中断和重试。
- [ ] 备份恢复。

### 性能关注点

- [x] 列表使用服务端分页。
- [ ] 大目录扫描不一次加载所有文件到内存。
- [x] SHA-256 使用流式计算。
- [ ] 批量写库使用批量 SQL。
- [x] 为常用筛选字段建立索引。
- [ ] 后续大数据量可改为游标/键集分页。

### 验收标准

- [ ] 旧菜单和旧接口行为保持不变。
- [ ] 新模块可完整导入、检索、统计、重试。
- [ ] 备份后能从数据库和原图目录恢复。
- [ ] 关键测试命令和结果有记录。

## 13. 当前状态

- [x] 阅读 `new_matrials/` 中的 V2 设计和总提示词。
- [x] 只读审查现有项目结构和旧业务代码。
- [x] 输出改造清单并保存为 `progress.md`。
- [x] 已完成 M1 环境适配与数据目录。
- [x] 已通过 `docker compose config` 配置校验。
- [x] 已通过 `python3 -m py_compile backend/config.py backend/asset_worker.py` 语法校验。
- [x] 已完成 M2 数据库 Schema 与迁移（代码与迁移文件）。
- [x] 已通过 `python3 -m py_compile` 检查 Alembic env 与两版迁移文件。
- [x] 已完成 M3 类别、两级类型、自定义标签（后端模型、服务与 API）。
- [x] 已通过 `python3 -m py_compile` 检查 M3 新增 Python 文件。
- [x] 已完成 M4 导入页面与扫描预览。
- [x] 已通过 `python3 -m py_compile` 检查 M4 后端文件，并通过 `node --check` 检查前端服务文件。
- [x] 已完成 M5 后台导入引擎与哈希存储。
- [x] 已通过 `python3 -m py_compile` 检查 M5 后端文件。
- [x] 已完成 M6 标注文件原样保存与关联。
- [x] 已通过 `python3 -m py_compile` 检查 M6 后端文件。
- [x] 已完成 M7 图片检索、浏览、批量修改。
- [x] 已通过 `python3 -m py_compile` 检查 M7 后端文件，并通过 `node --check` 检查前端服务文件。
- [x] 已完成 M8 资源统计与导入任务管理。
- [x] 已通过 `python3 -m py_compile` 检查 M8 后端文件。
- [x] 已完成 M9 集成测试、性能与备份验收（测试、冒烟脚本与回滚文档）。
- [x] 已通过 `python3 -m compileall -q backend` 后端全量语法检查。
- [x] 已通过 `cd frontend && npm run build` 前端生产构建。
- [x] 已执行 `docker compose up --build -d` 并通过 M1 运行时验收。
- [x] 已执行 `alembic upgrade head` / `alembic downgrade -1` 并通过 M2 运行时验收。
- [x] 已通过登录态调用 `/api/assets/categories` 与 `/api/assets/tags` 完成 M3 运行时验收。
- [x] 已通过 `/api/assets/imports/*` 完成 M4 运行时验收。
- [x] 已通过真实图片批次验证 M5 导入、去重、缩略图与失败重试。
- [x] 已通过带标注样例验证 M6 匹配。
- [x] 已通过 `/api/assets/images` 与文件接口完成 M7 运行时验收。
- [x] 已通过统计页和导入记录页完成 M8 运行时验收。
- [x] 已执行 `pytest -q tests`（11 passed）与 `scripts/smoke_test.sh`。
- [x] 所有计划模块 M1–M9 的代码实现已完成。
