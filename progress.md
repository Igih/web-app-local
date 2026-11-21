# 质量体检进度

## 第0阶段：工程审查和增量改造设计（已完成，未改代码/数据库/Compose）

- 已审查现有 Docker Compose、FastAPI、PostgreSQL、`asset_worker`、前端菜单和导入流程。
- 数据库当前为 Alembic `0002`，已有 `asset.import_batches` / `import_items` / `images` / `image_sources`，尚无 `quality_*` 表。
- 质量体检建议插入在 `awaiting_confirmation` 阶段，独立于现有 `confirm -> queued -> import` 流程。
- 完整设计见 [docs/quality-precheck-phase0-review.md](docs/quality-precheck-phase0-review.md)。

## 下一轮建议顺序

1. Q1：解码、指标计算、原始结果存储和缺失状态。
2. Q3 + Q5：画像规则、阈值约束、综合建议纯函数。
3. Q4：分布图、双阈值滑块、实时三态计数。
4. Q2：SHA 完全重复与 pHash 近重复。
5. Q6：评估快照、后台 CSV 导出和规则 JSON。

等待用户确认第0阶段设计后再开始 Q1。

## 实施状态（2026-11-20）

- 已按用户要求完成 Q1～Q6 的首版实现。
- Alembic 已升级到 `0003`，新增 `asset.quality_*` 表。
- `quality-worker` 已加入 Compose，并完成 1 张 smoke 和 1366 张红外图片实测。
- 后端全部单测通过：17 passed。
- 前端生产构建通过，`/assets/quality` 和 `/api` 链路已通过 HTTP 验证。
- 详细测试与限制见 [docs/quality-precheck-implementation-report.md](docs/quality-precheck-implementation-report.md)。
