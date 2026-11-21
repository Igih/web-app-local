# 入库前质量体检 Q1～Q6 实施与验收报告

> 生成时间：2026-11-20  
> 实施范围：仅对入库前候选文件夹做质量分析，不分析已入库历史图片，不自动触发正式入库。

> 2026-11-21 调整：当前质量评估仅使用模糊度、RMS 对比度、噪声估计和过曝比例四项。下文历史批次及测试数字记录的是本次调整前的验收结果。

## 1. 已实现模块

### Q1：指标计算与版本化存储

- 新增 `services/asset_quality/image_decoder.py`：
  - 支持 JPEG/PNG/BMP/WEBP/GIF 及 TIFF；
  - TIFF 使用 `tifffile`，保留 16-bit，未支持多页 TIFF；
  - EXIF 方向使用 Pillow 处理；
  - 长边固定缩放到 1024；
  - 固定 RGB→灰度权重 `[0.299, 0.587, 0.114]`；
  - 记录原始宽高、位深、通道、色彩模式、分析尺寸和缩放倍率。
- 新增 `services/asset_quality/metrics.py`：
  - 计算 `blur_effect/rms_contrast/noise_sigma/bright_fraction` 四项评估指标；
  - 记录噪声可信度及原始图像统计作为辅助元数据；
  - 保存 `raw_min/raw_max/P01/P99`；
  - 8-bit 归一化到 0～1，16-bit 保留原始统计并标记 `comparable=false`。
- 指标结果表：`asset.quality_metric_results`，唯一键为
  `(candidate_id, source_fingerprint, preprocess_version, algorithm_version)`，避免覆盖历史结果。

### Q2：SHA 完全重复与 pHash 近重复

- `asset.quality_candidates.sha256` 记录候选文件 SHA-256；
- 与正式库 `asset.images.sha256` 对比，记录 `existing_image_id`、`duplicate_scope=batch/library/both`；
- `asset.quality_library_phashes` 缓存正式库 64-bit pHash；
- 候选 pHash 与同批次、正式库计算 Hamming 距离；
- 批内 SHA 完全重复仅标记后出现的文件，保留首个候选；
- `asset.quality_neighbor_pairs` 保存最近邻配对；
- 搜索半径为 10，默认 pHash 近重复只触发复核，不自动排除。

### Q3 + Q5：画像规则、动态阈值与综合建议

- `asset.quality_profiles` 保存四类画像及未指定兜底画像；
- 默认规则可编辑、可保存新版本，旧版本保留；
- `quality_rule_engine` 纯函数执行：
  - 解码失败 → `exclude`；
  - SHA 完全重复 → `exclude`；
  - 严重指标且 `severe_enabled` → `exclude`；
  - 其他命中/缺失 → `review`；
  - 正常 → `admit`；
- 支持高值、低值规则；
- 临时阈值只通过 `evaluate-preview` 计算，不写入快照。

### Q4：前端质量仪表盘

- 新增 `AssetQualityDashboard.vue`；
- 新增 `MetricHistogramCard.vue`，使用 Chart.js 显示直方图并在阈值位置绘制竖线；
- 四个指标分别提供复核/严重滑块及严重自动排除开关；
- 复核与严重滑块独立调整；完全重复、解码失败等独立排除原因在页面单独提示；
- 候选图片默认收起，点击“建议复核”或“建议排除”后按当前阈值分页查看；点击缩略图打开最大 1600 像素预览；
- 候选缩略图和放大图通过携带登录令牌的 Axios 请求加载，翻页和关闭页面时释放临时浏览器图片地址；
- 支持防抖预览、候选分页、缩略图、固定评估、导出 CSV；
- 入口：
  - 新建导入扫描后点击“进入质量体检”；
  - 导入记录列表点击“体检”。

### Q6：评估快照与 CSV 导出

- `POST .../quality/evaluations` 固定候选集合、画像规则和指标版本；
- `asset.quality_evaluation_items` 保存逐图建议；
- 后台 Worker 生成 CSV 和 `quality_rules.json`；
- CSV 包含四项评估指标、重复信息、pHash、原因码、建议、版本和评估 ID；
- 空值不写 0；相对路径优先；UTF-8 BOM；公式注入防护；
- 导出结果记录行数、SHA-256 和状态。

## 2. 关键文件

后端新增：

- `backend/services/asset_quality/`
- `backend/routers/asset_quality.py`
- `backend/models/asset_quality.py`
- `backend/quality_worker.py`
- `backend/migrations/versions/0003_create_asset_quality_schema.py`
- `backend/tests/test_asset_quality_rules.py`

后端修改：

- `backend/requirements.txt`
- `backend/config.py`
- `backend/main.py`

部署修改：

- `compose.yaml` 新增 `quality-worker`

前端新增：

- `frontend/src/views/assets/AssetQualityDashboard.vue`
- `frontend/src/components/asset-quality/MetricHistogramCard.vue`
- `frontend/src/services/assetQualityService.js`

前端修改：

- `frontend/src/router/index.js`
- `frontend/src/views/assets/AssetImport.vue`
- `frontend/src/views/assets/AssetImportRecords.vue`
- `frontend/nginx.conf`

## 3. 实际测试结果

### 3.1 自动化测试

以下为调整前的历史测试记录。本次调整已使用一次性后端容器执行完整测试：`21 passed`；前端构建和 Python 语法检查也已通过。

```text
python -m pytest -q tests
17 passed in 0.78s
```

质量规则专项：

```text
python -m pytest -q tests/test_asset_quality_rules.py
6 passed in 0.60s
```

覆盖：

- 画像 key 生成；
- 高值/低值阈值边界；
- 解码失败排除；
- SHA 完全重复排除；
- 常量图指标计算。

### 3.2 小批次端到端

批次 1（1 张 smoke_assets 图片）：

```text
create job 200 {"job_id":1,"candidate_count":1}
job completed
candidate_progress {"total":1,"completed":1,"failed":0,"pending":0}
```

指标、直方图、候选、近重复、画像、评估预览、评估快照、CSV 导出接口均返回 200。

### 3.3 1366 张红外批次

批次 7（`/home/linux/Downloads/thermal_8_bit`）：

```text
create job 200 {"job_id":4,"candidate_count":1366}
job completed
candidate_progress {"total":1366,"completed":1366,"failed":0,"pending":0}
```

- 指标结果：1366 条；
- 近重复配对：2059 条；
- 最近邻 pHash 距离真实有效，不再为全零；
- 评估快照：`evaluation_id=3`，`item_count=1366`；
- CSV 导出：`row_count=1366`，文件 SHA-256 已记录；
- CSV 首行 pHash 为 `eb6370309e4f4395`。

### 3.4 前端生产路由

```text
GET /assets/quality/1 -> 200 text/html
GET /api/login -> 200
GET /api/assets/imports/7/quality/metrics -> 200
```

Nginx 到后端 API 链路已通过实际 HTTP 请求验证。

## 4. 已知限制与待完善

- 当前默认阈值为未校准占位值，不能作为生产自动排除依据。
- 当前测试数据中未发现 16-bit TIFF，16-bit 路径已实现但缺少真实样本回归。
- 前端浏览器交互（拖拽、图表视觉、缩略图）尚未进行人工点击验收，只验证了构建、路由和接口链路。
- 当前 pHash 搜索半径为 10；如果用户把阈值加大到超出该范围，需要提示扩展搜索，V1 尚未实现前端覆盖范围提示。
- 当前 Worker 会为每个新批次重建库内 pHash 缓存未命中的图片；首次全库缓存较慢，后续复用。
- 历史批次 6 的源目录已不存在，质量任务会标记 `source_exists=false`，不会伪造指标。

## 5. 回滚

数据库：

```bash
cd backend
alembic downgrade 0002
```

代码：

```bash
git revert <quality-commits>
```

容器：

```bash
docker compose stop quality-worker backend frontend
docker compose up -d db backend frontend asset-worker
```

新增质量文件目录：

```text
/srv/flower-assets/quality/
```

该目录可单独备份后删除，不影响正式原图和缩略图。
