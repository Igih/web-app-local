# 入库前质量体检 第0阶段工程审查与增量改造设计报告

> 生成时间：2026-11-20  
> 范围：只读审查，不修改代码、数据库、Docker 配置。  
> 依据：`new_matrials/图像入库前质量体检_详细设计方案_v1.md`、`new_matrials/代码Agent_入库前质量体检_分模块实施提示词_v1.md`。

## 0. 结论摘要

现有系统已经具备质量体检所需的绝大部分基础能力，但质量体检**不是**简单追加一个页面，而是要在现有“扫描预览 → 确认入库”之间插入一个独立的 `awaiting_confirmation` 质量分析阶段。

本次审查确认：

- 数据库当前版本为 `alembic 0002`，已有 `asset` schema 及 `import_batches`、`import_items`、`images`、`image_sources`、`import_issues` 等表。
- 当前数据库中没有 `quality_*` 表，代码中也没有质量指标、pHash、评估快照、CSV 导出的既有实现。
- 现有 `asset_worker` 只负责正式入库，质量指标应在新的独立 Worker 中执行，避免阻塞已有导入队列。
- 现有后端镜像只有 Pillow，没有 `numpy`、`opencv`、`scikit-image`、`imagehash`，Q1/Q2 需要增加依赖。
- 当前可观测样本主要是 8-bit JPEG（可见光 RGB 与红外灰度 L），尚未在项目目录中发现 16-bit TIFF 样本；16-bit 路径必须实现但需后续提供数据验证。

审查中发现的两个关键事实：

1. `import_items` 不是扫描时生成，而是在批次状态变为 `queued` 后由 `asset_worker._ensure_import_items()` 生成。因此质量体检**不能直接假设扫描预览阶段已经有 `import_items.id`**。
2. 历史批次 6 的源目录 `/home/linux/Downloads/outimg` 在当前宿主机已不存在，说明质量任务和 CSV 必须显式区分“源文件存在/缺失/扫描后变化”，不能只凭历史 `import_items` 认为源文件仍可用。

## 1. 真实项目结构与需要复用的组件

### 1.1 后端

现有后端不是设计文档中示例的 `backend/app/...` 深层结构，而是扁平结构：

```text
backend/
  main.py
  asset_worker.py
  config.py
  init_db.py
  routers/
    asset_import.py
    asset_images.py
    asset_overview.py
    asset_files.py
    asset_tags.py
    asset_categories.py
  services/
    asset_import.py
    asset_import_engine.py
    asset_storage.py
    asset_paths.py
    asset_thumbnails.py
    asset_annotations.py
    asset_stats.py
    asset_images.py
  models/
    asset_import.py
    asset_image.py
    asset_enums.py
  migrations/
    env.py
    versions/0001_create_asset_schema.py
    versions/0002_seed_asset_categories.py
```

可直接复用：

- 认证与权限：`services/auth.py` 的 `get_current_active_user`、`admin_required`。
- 路径安全：`services/asset_paths.validate_asset_path`、`is_image_file`、`iter_image_paths`。它已经处理绝对路径、符号链接越界、白名单根目录。
- 数据库连接：`utils/db.db_connection`、`db_transaction`，以及 Worker 中的 psycopg2 直连模式。
- SHA-256 与正式原图存储：`services/asset_storage.sha256_file`、`storage_key_for_sha256`。
- 缩略图生成：`services/asset_thumbnails.generate_thumbnail`，可扩展用于质量候选预览。
- 图片类别与两级类型：`models/asset_enums.CAPTURE_TYPES`、`SPECTRAL_TYPES`、`is_valid_type_pair`。
- 批次/候选来源：`asset.import_batches`、`asset.import_items`、`asset.images`、`asset.image_sources`。
- 迁移机制：`alembic` + `migrations/env.py` + 手写 SQL migration。当前版本为 `0002`。

不能直接复用或需要扩展的部分：

- `asset.import_items` 只能在 `queued` 后生成，不能作为扫描预览阶段稳定候选 ID。
- `asset_images` 目前只有正式图片 ID 的缩略图/原图下载接口，没有“未入库候选”的预览接口。
- 现有 `asset_worker` 的轮询逻辑只认 `import_batches.status = 'queued'`，不适合直接混入质量指标和 CSV 导出任务。
- `asset.images` 只保存宽高、格式和字节大小，没有位深、通道、EXIF 方向、pHash、指标字段，需要新建质量结果表。

### 1.2 前端

```text
frontend/src/
  router/index.js
  components/Layout.vue
  views/assets/AssetImport.vue
  views/assets/AssetImportRecords.vue
  views/assets/AssetOverview.vue
  views/assets/AssetImageManager.vue
  services/assetImportService.js
  services/assetService.js
  stores/auth.js
```

可直接复用：

- 登录态：`stores/auth.js`，主入口 `main.js` 已统一注入 Axios Authorization。
- UI 框架：Element Plus，已有表单、表格、分页、弹窗、开关、消息提示。
- 图表：`chart.js` + `chartjs-plugin-datalabels` + `vue-chartjs` 已在 `package.json`；HomePage 已使用 Chart.js。
- 导入服务：`assetImportService.js` 中的 `scanAssetImport`、`getAssetImportPreview`、`confirmAssetImport`。
- 图片缩略图加载模式：`AssetImageManager.vue` 的 `thumbnailUrls` / blob URL 缓存模式。
- CSV 前端导出习惯：`AssetOverview.vue` 使用 `\uFEFF` BOM + Blob 的客户端导出。但质量体检的 CSV 应按设计改为**服务端后台导出 + 受保护下载**，不应把全部行拉回浏览器。

### 1.3 运行环境

- `compose.yaml` 服务：`db`、`frontend`、`backend`、`asset-worker`。
- `db`：PostgreSQL 15，容器名 `web-app-local-31-db-1`。
- `backend`：FastAPI，入口 `main.py`，通过 `start.sh` 先 `python init_db.py`、再 `alembic upgrade head`、最后 `uvicorn ... --workers 8`。
- `asset-worker`：与 backend 共用镜像，命令 `python asset_worker.py`。
- 宿主机挂载：
  - `/home/linux/Downloads:/home/linux/Downloads:ro` 供 backend/worker/frontend 只读浏览。
  - `/srv/flower-assets:/srv/flower-assets:rw` 供 backend/worker 写入正式原图与缩略图。

## 2. 新质量流程在现有导入流程中的准确插入点

现有流程：

```text
用户填写导入表单
  -> POST /api/assets/imports/scan
  -> 创建 asset.import_batches(status='awaiting_confirmation')
  -> GET /api/assets/imports/{batch_id}/preview
  -> POST /api/assets/imports/{batch_id}/confirm
  -> status='queued'
  -> asset_worker process_next_queued_batch()
  -> _ensure_import_items()
  -> 逐图 store_original / 查 SHA / 入库 / 缩略图
```

建议插入点：

```text
scan
  -> batch.status = 'awaiting_confirmation'
  -> 可选：POST /api/assets/imports/{batch_id}/quality/jobs
       -> quality_worker 枚举源文件、计算 Q1/Q2
       -> 前端 QualityDashboard 查看指标、调整阈值
       -> 固定评估快照 / 导出 CSV
       -> 人工决定仍按原有 confirm 进入正式入库
  -> confirm
       -> batch.status = 'queued'
       -> asset_worker 正式入库
```

关键设计决定：

- 质量体检期间**不修改** `import_batches.status`，不改变现有 `confirm` 的语义。
- 质量任务状态放在新表 `asset.quality_jobs`，正式入库状态继续由 `import_batches.status` 和 `import_items.status` 表达。
- 质量体检只给建议和 CSV，不自动触发 `confirm`。用户确认规则后，仍可回到原导入页面点击“确认并加入队列”，这样不影响原流程。
- 对“历史已完成批次”的校准，可单独支持“从正式库 `asset.images` 构建分析集合”，但 V1 优先支持新批次 `awaiting_confirmation`。

## 3. Q1～Q6 需要新增和修改的文件清单

### 3.1 后端新增

建议按现有扁平风格，新增一个 `asset_quality` 服务包，而不是生造 `backend/app/` 目录。

```text
backend/services/asset_quality/
  __init__.py
  image_decoder.py
  source_fingerprint.py
  metric_registry.py
  metrics/
    __init__.py
    sharpness.py
    contrast.py
    exposure.py
    noise.py
    entropy.py
  duplicate_service.py
  histogram_service.py
  quality_rule_engine.py
  evaluation_service.py
  csv_export_service.py

backend/routers/
  asset_quality.py           # 或拆分为 jobs/metrics/profiles/evaluations/exports

backend/models/
  asset_quality.py           # Pydantic 请求/响应 DTO

backend/quality_worker.py    # 新后台 Worker 入口
```

### 3.2 后端修改

- `backend/main.py`：注册 `asset_quality` router。
- `backend/config.py`：新增 `ASSET_QUALITY_DIR`、`ASSET_QUALITY_PREVIEWS_DIR`、`ASSET_QUALITY_EXPORTS_DIR`、质量 Worker 轮询间隔等配置。
- `backend/requirements.txt`：增加 `numpy`、`opencv-python-headless`、`scikit-image`、`imagehash`（`imagehash` 会带来 `PyWavelets` 等间接依赖）。
- `backend/Dockerfile` 本身预计不需要改，因为 `requirements.txt` 变更后重建即可。
- `backend/migrations/versions/0003_create_asset_quality_schema.py`：新迁移。

### 3.3 Compose 修改

- `compose.yaml` 新增 `quality-worker` 服务：
  - 复用 `backend` 镜像；
  - `command: ["python", "quality_worker.py"]`；
  - 环境变量同 asset-worker，另加 `QUALITY_WORKER_POLL_INTERVAL`；
  - `volumes`：
    - `/srv/flower-assets:/srv/flower-assets:rw`
    - `/home/linux/Downloads:/home/linux/Downloads:ro`
  - `depends_on: db: condition: service_healthy`；
  - 保留独立 CPU/内存限制。

不修改现有 `db`、`backend`、`frontend`、`asset-worker` 服务定义，仅追加一个新服务。

### 3.4 前端新增

```text
frontend/src/views/assets/AssetQualityDashboard.vue
frontend/src/components/asset-quality/
  MetricHistogramCard.vue
  ThresholdControl.vue
  DuplicatePairViewer.vue
  CandidateImageGrid.vue
  RecommendationSummary.vue
  ExportDialog.vue
frontend/src/services/assetQualityService.js
```

### 3.5 前端修改

- `frontend/src/router/index.js`：新增 `/assets/quality/:batchId` 路由。
- `frontend/src/components/Layout.vue`：在“图像资源管理”菜单中新增“质量体检”入口，并补充 `activeIndex` 映射。
- `nginx/nginx.conf`：为 `/assets/quality` 增加 Vue history 回退规则，避免 `/assets/` 静态块把该路径返回 404。
- `frontend/src/services/assetImportService.js`：可在扫描预览成功后增加“进入质量体检”入口，但更稳妥的是在 `AssetImport.vue` 中增加一个跳转按钮，不改变现有 `confirm` 行为。

## 4. 数据库迁移方案及兼容性风险

### 4.1 新表建议

全部放在现有 `asset` schema，不触碰 `public` 旧表，也不修改 `asset.import_batches` 的现有 CHECK 约束。

建议逻辑表：

| 表 | 用途 | 关键约束 |
|---|---|---|
| `quality_jobs` | Q1/Q2 后台任务状态和进度 | `batch_id` 外键；`state` 状态机；`retry_count`；`error` |
| `quality_candidates` | 入库前候选清单 | 唯一 `(batch_id, normalized_relative_path)`；保存 `source_path`、指纹、解码元数据、画像 key |
| `quality_metric_results` | 原始指标结果 | 唯一 `(candidate_id, source_fingerprint, preprocess_version, algorithm_version)`，避免错误覆盖历史结果 |
| `quality_neighbor_pairs` | pHash 近重复候选对 | 保存距离、`scope=batch/library`、搜索版本、覆盖状态 |
| `quality_profiles` | 四类画像 + 未指定兜底规则版本 | 唯一 `(profile_key, version)`；`config_jsonb`；`status` |
| `quality_evaluations` | 用户确认的评估快照 | `batch_id`、候选集合 hash、规则快照、创建者 |
| `quality_evaluation_items` | 快照逐图结果 | 唯一 `(evaluation_id, candidate_id)`；`recommendation`、`flags_jsonb` |
| `quality_manual_reviews` | 人工覆盖和审核历史 | `candidate_id`、`manual_decision`、`reviewed_by`、`reviewed_at` |
| `quality_exports` | CSV 导出任务和文件元数据 | `evaluation_id`、`storage_key`、`row_count`、`file_sha256` |

### 4.2 索引

- `quality_candidates(batch_id)`、唯一 `(batch_id, normalized_relative_path)`。
- `quality_metric_results(candidate_id)`、唯一 `(candidate_id, source_fingerprint, preprocess_version, algorithm_version)`。
- `quality_metric_results` 按批次分析时可能需要 `(batch_id, profile_key)`，可通过 join `quality_candidates` 完成；若量大可加冗余 `batch_id` 列。
- `quality_neighbor_pairs(left_candidate_id)`、`(right_candidate_id)`、`(distance)`。
- `quality_profiles(profile_key, version)`。
- `quality_evaluations(batch_id, created_at)`。
- `quality_evaluation_items(evaluation_id, recommendation)`。
- `quality_exports(evaluation_id, state)`。

### 4.3 迁移方式

新增 `backend/migrations/versions/0003_create_asset_quality_schema.py`，沿用现有 `op.execute()` 手写 SQL 风格。`downgrade` 仅 drop 本迁移新增表/索引，**不** `DROP SCHEMA asset CASCADE`，以免误删现有资产表。

### 4.4 兼容性风险

- **不动 `import_batches.status` CHECK**：质量阶段状态独立到 `quality_jobs`，避免迁移需要改旧约束。
- **不动 `import_items` 的唯一约束和状态机**：质量候选与正式导入条目分离，避免 `pending/imported/duplicate/failed` 混入 `quality` 状态。
- **历史数据源文件可能缺失**：批次 6 的 `/home/linux/Downloads/outimg` 已不在当前宿主目录。质量任务应记录 `source_exists=false`，不要假设所有历史候选都可重测。
- **指标不可覆盖历史快照**：唯一键包含 `source_fingerprint + preprocess_version + algorithm_version`；重新计算生成新版本，不覆盖已引用结果。
- **16-bit 与 8-bit 不得混用绝对阈值**：profile 必须包含位深信息；未指定/未知量程时 `comparable=false`。
- **回滚**：`0003` downgrade 只删除新增表；已有 `asset` 表不受影响。

## 5. Q1～Q6 的依赖关系、实施顺序和 API 契约

### 5.1 依赖关系

```text
Q1 指标计算 + 存储
        |
        +---> Q2 重复检测（SHA/pHash）
        |
        +---> Q3 规则配置 + Q5 建议引擎
                        |
                        +---> Q4 前端分布图/滑块/联动
                        |
                        +---> Q6 快照与 CSV 导出
```

推荐实施顺序：

1. **Q1**：解码、指标、版本化存储、缺失状态和单元测试。
2. **Q3 + Q5**：规则版本、画像、阈值约束、纯函数建议引擎。
3. **Q4**：仪表盘、每指标分布图、图下双阈值滑块、实时三态计数。
4. **Q2**：SHA 完全重复 + pHash 近重复（后续完善）。
5. **Q6**：冻结评估快照、后台 CSV 导出、规则 JSON。

这与用户要求的 `Q1 → Q3+Q5 → Q4 → Q2/Q6` 一致。

### 5.2 建议 API 契约

实际代码使用 `/api` 前缀，`asset_import` 路由前缀为 `/assets/imports`。建议保持统一：

```text
POST   /api/assets/imports/{batch_id}/quality/jobs
GET    /api/assets/quality/jobs/{job_id}

GET    /api/assets/imports/{batch_id}/quality/metrics
GET    /api/assets/imports/{batch_id}/quality/histograms
POST   /api/assets/imports/{batch_id}/quality/evaluate-preview
GET    /api/assets/imports/{batch_id}/quality/candidates
GET    /api/assets/imports/{batch_id}/quality/near-duplicates

GET    /api/assets/quality/profiles
PUT    /api/assets/quality/profiles/{profile_id}

POST   /api/assets/imports/{batch_id}/quality/evaluations
POST   /api/assets/quality/reviews

POST   /api/assets/quality/evaluations/{evaluation_id}/exports
GET    /api/assets/quality/exports/{export_id}
GET    /api/assets/quality/exports/{export_id}/download
```

候选预览建议增加：

```text
GET /api/assets/quality/candidates/{candidate_id}/thumbnail
```

该接口只允许读取授权批次内的候选预览，不能使用 `asset.images` 的正式图片接口。

### 5.3 evaluate-preview 契约

请求：

```json
{
  "request_id": "ui-38",
  "filters": {
    "category": "rose",
    "capture_type": "photo",
    "spectral_type": "infrared"
  },
  "profile_key": "photo_infrared_8bit",
  "draft_rules": {
    "blur_effect": {"enabled": true, "review": 0.50, "severe": 0.80}
  }
}
```

响应：

```json
{
  "request_id": "ui-38",
  "evaluated_count": 1000,
  "pending_count": 0,
  "counts": {"admit": 720, "review": 240, "exclude": 40},
  "flag_counts": {"BLUR_SUSPECT": 200, "LOW_CONTRAST": 60},
  "profile_calibrated": false,
  "stale": false
}
```

`flag_counts` 允许重叠，不能简单相加得到 `counts`。

### 5.4 单指标卡片契约

前端每个指标卡片只消费后端统一结构：

```json
{
  "metric_id": "blur_effect",
  "display_name": "模糊程度",
  "direction": "high",
  "unit": "0~1",
  "scope": "photo_visible_8bit",
  "histogram": {"edges": [0.0, 0.2, 0.4, 0.6, 0.8, 1.0], "counts": [80, 150, 60, 30, 10]},
  "missing_count": 3,
  "thresholds": {"review": 0.55, "severe": 0.85, "severe_enabled": false},
  "threshold_editable": true,
  "algorithm_version": "blur_v1"
}
```

## 6. 四种图片类型的质量指标处理规则

### 6.1 画像 key

```text
photo_visible
photo_infrared
hand_drawn_visible
hand_drawn_infrared
unspecified
```

建议 key 加入位深，例如：

```text
photo_visible_8bit
photo_infrared_8bit
photo_infrared_16bit
hand_drawn_visible_8bit
hand_drawn_infrared_8bit
```

位深未知或非 8/16-bit 时进入 `unspecified` 或标记为待复核。

### 6.2 统一预处理

- 先记录原始文件 SHA-256、文件大小、解码状态、宽高、通道数、色彩模式、位深、原始数值范围、EXIF 方向和源文件 mtime/size。
- 使用 `IMREAD_UNCHANGED | IMREAD_ANYDEPTH` 或 `tifffile` 保留 16-bit；Pillow 只作为现有缩略图辅助，不作为 Q1 数值计算的唯一依赖。
- 只在内存分析副本上做灰度与缩放，不写回原图。
- 分析尺度固定：长边缩放至 1024，不放大；记录 `analysis_width/height/scale`。
- 灰度固定为 `Y = 0.299R + 0.587G + 0.114B`；L 模式灰度图直接作为单通道处理。Alpha 策略需在 Q1 中明确：建议统一以白底合成或按 `matte` 处理并记录到 `preprocess_config`。
- 8-bit 统一到 0～1；16-bit 保存 `raw_min/raw_max/P01/P99`，不能仅做单张 min-max 归一化后判定原始对比度。

### 6.3 四类画像默认规则

以下阈值仅为 V1 候选，**未经校准，不作为删除或自动排除依据**：

| 指标 | 实拍可见光 | 实拍红外 | 手绘可见光 | 手绘红外 | 特殊处理 |
|---|---|---|---|---|---|
| `blur_effect` | 高值复核 | 高值复核 | 需谨慎，手绘边缘可能天然高频 | 需谨慎 | 严重自动排除默认关闭 |
| `lap_var` | 低值复核 | 低值复核 | 默认只提示 | 默认只提示 | 与 Tenengrad 组合使用 |
| `tenengrad` | 低值复核 | 低值复核 | 默认只提示 | 默认只提示 | 与 Laplacian 组合使用 |
| `rms_contrast` | 低值复核 | 必须使用固定量程/相对异常 | 低值复核 | 固定量程/相对异常 | 16-bit 未知量程 `comparable=false` |
| `p99_p1` | 低值复核 | 记录原始单位和归一化值 | 低值复核 | 记录原始单位和归一化值 | 不直接跨位深比较 |
| `mean_brightness` | 双端暗/亮 | 双端暗/亮，但亮阈值与可见光过曝不等价 | 双端暗/亮 | 双端暗/亮 | 双端需要四个边界 |
| `dark_fraction` | 高值复核 | 高值复核 | 高值复核 | 高值复核 | 暗像素阈值固定记录 |
| `bright_fraction` | 高值复核 | 高值复核，但需谨慎 | 高值复核 | 高值复核 | 红外高亮不等于可见光过曝 |
| `noise_sigma` | 高值复核 | 高值复核，可信度降低 | 高值复核 | 高值复核 | 纹理复杂只复核不强排 |
| `entropy_8bit` | 低值复核 | 低值复核 | 低熵可能正常，严重排除默认关闭 | 低熵可能正常，严重排除默认关闭 | 256-bin 固定量化 |
| `width/height/pixels` | 可选最小尺寸 | 可选最小尺寸 | 可选最小尺寸 | 可选最小尺寸 | 独立于感知质量 |

画像规则的存储必须包含：

```json
{
  "profile_key": "photo_visible_8bit",
  "version": 1,
  "preprocess_version": "preprocess_v1",
  "metrics": {
    "blur_effect": {
      "enabled": true,
      "direction": "high",
      "review": 0.55,
      "severe": 0.85,
      "severe_enabled": false
    }
  },
  "exact_duplicate_policy": "skip_new_file_keep_source",
  "near_duplicate_policy": "review",
  "missing_metric_policy": "review"
}
```

### 6.4 判定规则

- 阈值方向约束：高风险高值 `review <= severe`；高风险低值 `severe <= review`；亮度双端 `dark_severe <= dark_review < bright_review <= bright_severe`。
- 边界比较统一：高值使用 `>=`，低值使用 `<=`。
- 一张图片可以同时有多个原因码，但综合建议只有 `admit/review/exclude` 一个。
- `severe` 是否转 `exclude` 取决于 `severe_enabled`，不能默认排除。
- 16-bit 红外量程未知时，量程相关严重阈值禁用或降级为复核。
- 未指定画像使用 `unspecified` 兜底，默认不做强推断。

## 7. 分布图、动态滑块和综合建议的具体实现方式

### 7.1 分布图

- 由后端 `histogram_service` 预计算 40～100 bins/指标/画像/过滤器。
- 前端 `MetricHistogramCard` 用 Chart.js 渲染柱状图；阈值线可用 Chart.js 自定义 annotation 或 overlay div/SVG 实现。
- 高偏态指标支持 log 视图；离散指标（`decode_status`、SHA 完全重复）使用分类柱图，不用滑块。
- 图表必须显示缺失值数量，不能把 NULL 画成 0。

### 7.2 动态滑块

- 每个数值指标卡片下方放两个滑块：复核阈值、严重阈值；亮度指标用两个区间或四个滑块表示暗/亮边界。
- 拖动时本地立即更新数值和竖线，250～400ms 防抖后调用 `evaluate-preview`。
- 请求带 `request_id` 或单调序号，前端只接受最新响应，防止旧请求覆盖新配置。
- 拖动只读已存指标重算规则，**不重新解码图片**。
- 临时预览不写 `quality_evaluations`；点击“保存规则/固定评估”才生成正式版本。

### 7.3 综合建议

- 后端实现纯函数 `quality_rule_engine`：

```text
decode failed              -> exclude
exact duplicate            -> exclude（仅指不新增物理原图）
source changed after scan  -> review
severe rule enabled        -> exclude
warn/severe rule           -> review
required metric unavailable -> review
otherwise                  -> admit
```

- 三态计数必须逐图计算，不能把各指标命中数相加。
- 第一版直接用 SQL/共享 Python 评估逻辑对当前过滤候选逐图计算；缓存、位图等作为性能优化放在压测之后。
- `flag_counts` 只做展示，不能用于推导综合计数。

## 8. CSV 导出和评估快照的实现方案

### 8.1 评估快照

- `POST .../quality/evaluations` 在事务中冻结：
  - 候选集合（批次/过滤范围）；
  - 当前画像规则版本和 `preprocess_version`；
  - 指标版本；
  - 源文件指纹。
- 逐候选生成 `quality_evaluation_items`，保存 `recommendation` 和 `flags_jsonb`。
- 快照创建后，后续阈值变化不影响该快照。
- 源文件在冻结后变化时，标记快照过期或重新测量，不能把旧指标冒充当前文件结果。

### 8.2 CSV 字段

建议复用设计文档字段：

```text
batch_id,candidate_id,source_relative_path,original_filename,
category,capture_type,spectral_type,width,height,bit_depth,channels,file_size,
sha256,decode_status,decode_error,content_changed,
lap_var,tenengrad,blur_effect,rms_contrast,p99_p1,
mean_brightness,dark_fraction,bright_fraction,noise_sigma,noise_confidence,entropy_8bit,
exact_duplicate,duplicate_scope,existing_image_id,
phash_64,phash_nearest_distance,nearest_image_id,nearest_candidate_id,
quality_flags,recommendation,manual_decision,manual_reason,
metric_version,preprocess_version,profile_key,profile_version,evaluation_id,exported_at
```

### 8.3 后台导出

- `quality-worker` 读取已确认的 `quality_evaluation_items`，不读取在线滑块临时状态。
- 游标/批次流式写入 `*.csv.part`，完成校验后原子 rename。
- UTF-8 输出，可选 BOM 方便 Excel；规则 JSON 同时导出 `quality_rules.json`。
- CSV 记录 `row_count`、`file_sha256`、`state`。
- 下载接口需要登录态和批次权限校验；不把百万行拼接到 FastAPI 内存。
- 字符串字段需防止 Excel 公式注入，外部路径优先写相对路径。

## 9. 测试计划、性能风险和回滚方式

### 9.1 测试计划

后端单元测试：

- 路径扫描、授权目录、符号链接越界；
- 图像解码：常量图、清晰边缘、高斯模糊、加噪声、暗图、亮图、低对比度、透明 PNG、旋转 EXIF、损坏文件；
- 指标趋势与阈值边界；
- 规则约束和综合建议边界；
- 快照不可变、人工覆盖不被重算覆盖；
- CSV 转义、空值、中文、逗号路径、公式注入防护。

后端集成测试：

- 用 FastAPI `TestClient` 走 scan → quality job → evaluate-preview → snapshot → export 全链路；
- Worker 重试、中断、幂等、容器重建；
- 源文件在扫描后变化时能进入 `review/重测`；
- 原有 `asset_import`、`asset_images`、`asset_overview` 回归测试。

前端测试：

- 指标卡片渲染和阈值方向；
- 滑块防抖和过期响应丢弃；
- 三态计数与后端响应一致；
- 候选缩略图分页和人工覆盖交互。

性能测试：

- 分 1k、10k、100k、100万候选记录 P50/P95；
- 指标计算缓存命中耗时；
- `evaluate-preview` 在 10万/100万下的响应时间；
- pHash 构建和近邻查询耗时；
- CSV 导出速度和内存峰值。

### 9.2 性能风险

- 全量解码和指标计算是最大开销，不能放进 Web 请求同步执行。
- 指标结果必须按 `source_fingerprint + preprocess_version + algorithm_version` 复用。
- pHash 不能对百万张全量两两比较；小规模用 BK-tree，大规模需分桶/二进制向量索引并记录搜索覆盖范围。
- 三态精确计数需要逐图联合规则，不能只靠一维直方图边缘分布。
- 前端不得一次性加载百万候选；缩略图分页加载。
- 后端镜像缺少 numpy/opencv/skimage/imagehash，必须在 Q1 前解决依赖和镜像体积。

### 9.3 回滚方式

代码级回滚：

```bash
docker compose stop quality-worker backend frontend
git revert <quality-commits>
cd backend && alembic downgrade 0002
docker compose up -d db backend frontend asset-worker
```

数据库回滚：

- 新增迁移 `0003` 的 `downgrade` 仅 drop 新增 `quality_*` 表/索引，不 drop `asset` schema。
- 不修改现有 `asset.import_batches`、`import_items`、`images` 约束，因此回滚不会影响旧数据。

文件回滚：

- 质量预览和导出文件位于 `/srv/flower-assets/quality_previews`、`/srv/flower-assets/quality_exports`，可按目录备份后删除。
- 正式原图 `originals/` 和缩略图 `thumbnails/` 不在质量模块写入范围内，Q1/Q2 只读。

## 10. 待核实事项

以下内容当前无法从代码或可访问环境中完全确认，需要在 Q1 实施前验证：

1. 当前项目目录未发现 16-bit TIFF 样本，`photo_infrared_16bit` 的 `tifffile` 解码和固定辐射量程需要用户提供真实样本。
2. 历史批次 6 的 `/home/linux/Downloads/outimg` 源目录已不存在；若要对历史批次做校准，需要确认正式库 `/srv/flower-assets/originals` 是否为唯一可靠数据来源。
3. 手绘可见光样本当前数据库中未见，`hand_drawn_visible` 画像阈值只能先作为占位配置。
4. 当前数据库 `asset.images` 没有位深/通道/EXIF 字段，Q1 需要从源文件重新计算；历史批次若源文件缺失，只能从正式原图反推，无法恢复 EXIF 和完整原始值域。
5. 现有前端已有 Chart.js，但尚无通用 histogram/annotation 组件，Q4 需要新增组件，不能直接复用 HomePage 的饼图/条形图。
6. 当前 nginx `/assets/` 静态块对 `/assets/quality` 的 Vue 历史路由不友好，必须验证并新增 location 规则。
7. 现有 `asset_worker` 与计划中的 `quality_worker` 是否会并发访问同一批源文件，需要在实际环境中确认 I/O 压力。
8. 是否允许质量预览缩略图写入 `/srv/flower-assets/quality_previews`，需用户在 Q1 实施前确认目录规划。

