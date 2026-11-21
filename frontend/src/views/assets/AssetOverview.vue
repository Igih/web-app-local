<template>
  <div v-loading="loading" class="asset-overview-page">
    <div v-if="error" class="state-panel error-state">
      <svg class="state-icon" aria-hidden="true">
        <use href="/icons/mdi.svg#alert-circle-outline"></use>
      </svg>
      <h2>统计数据加载失败</h2>
      <p>请确认后端服务与当前账户权限正常。</p>
      <button class="primary-btn" @click="loadStats">
        <svg class="button-icon" aria-hidden="true">
          <use href="/icons/mdi.svg#refresh"></use>
        </svg>
        重新加载
      </button>
    </div>

    <template v-else>
      <header class="page-hero">
        <div class="hero-copy">
          <!-- <div class="eyebrow">
            <span class="pulse-dot"></span>
            ASSET://OVERVIEW
            <span class="eyebrow-muted">· 自动校验节点运行中</span>
          </div> -->
          <h1>图像资源统计与多维分析</h1>
          <p>汇总唯一图像、来源文件与重复/损坏/冲突状态，并拆解采集方式、光谱类型和类别分布。</p>
        </div>
        <div class="hero-actions">
          <div v-if="lastUpdated" class="sync-meta">
            <svg class="sync-icon" aria-hidden="true">
              <use href="/icons/mdi.svg#clock-outline"></use>
            </svg>
            最近同步 {{ lastUpdated }}
          </div>
          <button class="ghost-btn" :disabled="loading" @click="loadStats">
            <svg class="button-icon" aria-hidden="true">
              <use href="/icons/mdi.svg#refresh"></use>
            </svg>
            刷新数据
          </button>
          <button class="primary-btn" :disabled="!categoryRows.length" @click="exportCsv">
            <svg class="button-icon" aria-hidden="true">
              <use href="/icons/mdi.svg#download"></use>
            </svg>
            导出 CSV
          </button>
        </div>
      </header>

      <section class="kpi-grid" aria-label="核心指标">
        <article
          v-for="card in kpiCards"
          :key="card.key"
          class="kpi-card"
          :style="{ '--accent': card.accent }"
        >
          <div class="kpi-card-top">
            <span class="kpi-label">{{ card.label }}</span>
            <svg class="kpi-icon" aria-hidden="true">
              <use :href="`/icons/mdi.svg#${card.icon}`"></use>
            </svg>
          </div>
          <div class="kpi-value">{{ card.display }}</div>
          <div class="kpi-meta">{{ card.meta }}</div>
        </article>
      </section>

      <section class="analytics-grid">
        <article class="panel distribution-panel">
          <div class="panel-header">
            <div>
              <div class="panel-title-row">
                <h2>采集方式与光谱分布拓扑</h2>
                <span class="tech-chip">离线矢量渲染</span>
              </div>
              <p>跨可见光、近红外（NIR）及手绘草图的模态配比与空缺统计。</p>
            </div>
          </div>
          <div class="distribution-layout">
            <div class="bar-panel">
              <div class="bar-panel-header">
                <span>模态样本分布直方图</span>
                <span>单位：张</span>
              </div>
              <div class="bar-chart">
                <div v-for="item in distribution" :key="item.key" class="bar-column">
                  <div class="bar-value">{{ formatCompact(item.value) }}</div>
                  <div class="bar-track">
                    <div
                      class="bar-fill"
                      :style="{ height: barHeight(item.value), background: item.color }"
                    ></div>
                  </div>
                  <div class="bar-label">{{ item.label }}</div>
                  <div class="bar-percent">{{ formatPercent(item.percent) }}</div>
                </div>
              </div>
            </div>
            <div class="donut-panel">
              <div class="donut-heading">
                <span>全模态占比环形切片</span>
                <span>总计 100%</span>
              </div>
              <div class="donut-chart">
                <svg viewBox="0 0 160 160" class="donut-svg">
                  <circle
                    cx="80"
                    cy="80"
                    r="64"
                    fill="transparent"
                    stroke="#e2e8f0"
                    stroke-width="18"
                  ></circle>
                  <circle
                    v-for="segment in donutSegments"
                    :key="segment.key"
                    cx="80"
                    cy="80"
                    r="64"
                    fill="transparent"
                    :stroke="segment.color"
                    :stroke-dasharray="segment.dasharray"
                    :stroke-dashoffset="segment.dashoffset"
                    stroke-width="18"
                  ></circle>
                </svg>
                <div class="donut-center">
                  <strong>{{ formatNumber(grandTotal) }}</strong>
                  <span>样本总量</span>
                </div>
              </div>
              <div class="donut-legend">
                <div v-for="item in distribution" :key="item.key" class="legend-row">
                  <span class="legend-dot" :style="{ background: item.color }"></span>
                  <span class="legend-label">{{ item.label }}</span>
                  <strong>{{ formatPercent(item.percent) }}</strong>
                </div>
              </div>
            </div>
          </div>
        </article>

        <aside class="panel health-panel">
          <div class="panel-header">
            <div>
              <h2>数据质量健康度</h2>
              <p>基于采集与光谱元数据的完整度评估。</p>
            </div>
            <svg class="panel-icon" aria-hidden="true">
              <use href="/icons/mdi.svg#speedometer"></use>
            </svg>
          </div>
          <div class="health-gauge">
            <svg viewBox="0 0 120 120" class="gauge-svg">
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="transparent"
                stroke="#e2e8f0"
                stroke-width="9"
              ></circle>
              <circle
                cx="60"
                cy="60"
                r="50"
                fill="transparent"
                stroke="#0891b2"
                stroke-width="9"
                stroke-linecap="round"
                :stroke-dasharray="gaugeCircumference"
                :stroke-dashoffset="gaugeOffset"
              ></circle>
            </svg>
            <div class="gauge-center">
              <strong>{{ formatPercent(gaugePercent) }}</strong>
              <span>完整光谱标注率</span>
            </div>
          </div>
          <div class="health-metrics">
            <div class="health-row">
              <svg class="health-icon tertiary" aria-hidden="true">
                <use href="/icons/mdi.svg#check-circle-outline"></use>
              </svg>
              <span>完整模态样本</span>
              <strong>{{ formatNumber(completeCount) }}</strong>
            </div>
            <div class="health-row">
              <svg class="health-icon slate" aria-hidden="true">
                <use href="/icons/mdi.svg#help-circle-outline"></use>
              </svg>
              <span>未指定光谱</span>
              <strong>{{ formatNumber(unspecifiedCount) }}</strong>
            </div>
            <div class="health-row">
              <svg class="health-icon danger" aria-hidden="true">
                <use href="/icons/mdi.svg#alert-circle-outline"></use>
              </svg>
              <span>类型未指定</span>
              <strong>{{ formatNumber(typeUnspecifiedCount) }}</strong>
            </div>
          </div>
        </aside>
      </section>

      <section class="panel category-matrix-panel">
        <div class="panel-header matrix-header">
          <div>
            <div class="panel-title-row">
              <h2>花卉品类多光谱矩阵分布</h2>
              <span class="tech-chip">Top {{ categoryRows.length }} 分类</span>
            </div>
            <p>按可见光、红外与手绘模态横向对比各分类样本丰富度。</p>
          </div>
        </div>
        <div class="category-card-grid">
          <article v-for="row in categoryCards" :key="row.id" class="category-card">
            <div class="category-card-head">
              <div>
                <h3>{{ row.displayName }}</h3>
                <span>{{ row.name }}</span>
              </div>
              <strong>{{ formatNumber(row.total) }}</strong>
            </div>
            <div class="mini-chart">
              <div v-for="metric in row.metrics" :key="metric.key" class="mini-column">
                <span class="mini-value">{{ formatCompact(metric.value) }}</span>
                <div class="mini-track">
                  <div
                    class="mini-fill"
                    :style="{
                      height: miniBarHeight(metric.value, row.maxMetric),
                      background: metric.color,
                    }"
                  ></div>
                </div>
                <span class="mini-label">{{ metric.label }}</span>
              </div>
            </div>
            <div class="category-card-foot">
              <span>占总样本</span>
              <strong>{{ formatPercent(shareFor(row.total)) }}</strong>
            </div>
          </article>
        </div>
      </section>

      <section class="panel table-panel">
        <div class="table-toolbar">
          <div>
            <div class="panel-title-row">
              <h2>类别-模态交叉细分分析</h2>
              <span class="tech-chip">共 {{ categoryRows.length }} 类</span>
            </div>
          </div>
          <div class="table-actions">
            <div class="search-box">
              <svg class="search-icon" aria-hidden="true">
                <use href="/icons/mdi.svg#magnify"></use>
              </svg>
              <input v-model.trim="keyword" type="text" placeholder="搜索分类名称或编码..." />
            </div>
            <button class="ghost-btn compact" :disabled="!filteredRows.length" @click="exportCsv">
              <svg class="button-icon" aria-hidden="true">
                <use href="/icons/mdi.svg#download"></use>
              </svg>
              导出 CSV
            </button>
          </div>
        </div>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>类别</th>
                <th class="num">实拍·可见光</th>
                <th class="num">实拍·红外</th>
                <th class="num">手绘·可见光</th>
                <th class="num">手绘·红外</th>
                <th class="num">实拍·未指定</th>
                <th class="num">手绘·未指定</th>
                <th class="num">类型未指定</th>
                <th class="num">合计</th>
                <th>占比权重</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in filteredRows" :key="row.id">
                <td>
                  <div class="category-cell">
                    <span class="category-avatar">
                      <svg class="category-icon" aria-hidden="true">
                        <use href="/icons/mdi.svg#flower"></use>
                      </svg>
                    </span>
                    <div>
                      <strong>{{ row.displayName }}</strong>
                      <small>{{ row.name }}</small>
                    </div>
                  </div>
                </td>
                <td class="num"><span class="badge primary-badge">{{ formatNumber(row.photoVisible) }}</span></td>
                <td class="num"><span class="badge tertiary-badge">{{ formatNumber(row.photoInfrared) }}</span></td>
                <td class="num"><span class="badge secondary-badge">{{ formatNumber(row.handDrawnVisible) }}</span></td>
                <td class="num"><span class="badge deep-secondary-badge">{{ formatNumber(row.handDrawnInfrared) }}</span></td>
                <td class="num"><span class="badge muted-badge">{{ formatNumber(row.photoUnspecified) }}</span></td>
                <td class="num"><span class="badge muted-badge">{{ formatNumber(row.handDrawnUnspecified) }}</span></td>
                <td class="num"><span class="badge danger-badge">{{ formatNumber(row.typeUnspecified) }}</span></td>
                <td class="num"><strong>{{ formatNumber(row.total) }}</strong></td>
                <td>
                  <div class="share-cell">
                    <div class="share-track">
                      <div class="share-fill" :style="{ width: `${shareFor(row.total)}%` }"></div>
                    </div>
                    <span>{{ formatPercent(shareFor(row.total)) }}</span>
                  </div>
                </td>
              </tr>
              <tr v-if="!filteredRows.length">
                <td colspan="10" class="empty-cell">未找到匹配分类</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="table-summary">
          <div>
            <span>汇总校验：</span>
            <strong>{{ formatNumber(grandTotal) }}</strong> 唯一图像
            <span class="summary-divider"></span>
            <strong>{{ formatNumber(totals.duplicates || 0) }}</strong> 待剪枝冗余
          </div>
          <div class="summary-hint">
            <span class="status-dot"></span>
            完整模态占比 {{ formatPercent(gaugePercent) }}
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const stats = ref(null)
const loading = ref(false)
const error = ref(false)
const keyword = ref('')
const lastUpdated = ref('')

const categories = computed(() => stats.value?.categories || [])
const totals = computed(() => stats.value?.totals || {})

const asNumber = (value) => Number(value || 0)

const categoryRows = computed(() =>
  categories.value.map((row, index) => {
    const combinations = row.combinations || {}
    const photoVisible = asNumber(combinations.photo_visible)
    const photoInfrared = asNumber(combinations.photo_infrared)
    const handDrawnVisible = asNumber(combinations.hand_drawn_visible)
    const handDrawnInfrared = asNumber(combinations.hand_drawn_infrared)
    const photoUnspecified = asNumber(row.photo_unspecified)
    const handDrawnUnspecified = asNumber(row.hand_drawn_unspecified)
    const typeUnspecified = asNumber(row.type_unspecified)
    const handDrawnTotal = handDrawnVisible + handDrawnInfrared
    const total =
      photoVisible +
      photoInfrared +
      handDrawnVisible +
      handDrawnInfrared +
      photoUnspecified +
      handDrawnUnspecified +
      typeUnspecified

    return {
      id: row.id ?? index,
      name: row.name || '',
      displayName: row.display_name || row.name || `分类 ${index + 1}`,
      photoVisible,
      photoInfrared,
      handDrawnVisible,
      handDrawnInfrared,
      photoUnspecified,
      handDrawnUnspecified,
      typeUnspecified,
      handDrawnTotal,
      total,
    }
  }),
)

const categoryTotal = computed(() =>
  categoryRows.value.reduce((sum, row) => sum + row.total, 0),
)

const grandTotal = computed(() =>
  asNumber(totals.value.unique_images) || categoryTotal.value,
)

const formatNumber = (value) =>
  new Intl.NumberFormat('zh-CN').format(Math.round(asNumber(value)))

const formatCompact = (value) => {
  const number = asNumber(value)
  if (number >= 10000) {
    const short = number / 10000
    return `${Number(short.toFixed(short >= 100 ? 0 : 1))}万`
  }
  return formatNumber(number)
}

const percentage = (part, total) => {
  const safeTotal = asNumber(total)
  return safeTotal ? (asNumber(part) / safeTotal) * 100 : 0
}

const formatPercent = (value) => `${Number(asNumber(value).toFixed(1))}%`

const shareFor = (value) => percentage(value, grandTotal.value)

const distribution = computed(() => {
  const sum = (key) =>
    categoryRows.value.reduce((total, row) => total + asNumber(row[key]), 0)

  return [
    { key: 'photoVisible', label: '实拍·可见光', value: sum('photoVisible'), color: '#2563eb' },
    { key: 'photoInfrared', label: '实拍·红外', value: sum('photoInfrared'), color: '#0891b2' },
    { key: 'handDrawnVisible', label: '手绘·可见光', value: sum('handDrawnVisible'), color: '#7c3aed' },
    { key: 'handDrawnInfrared', label: '手绘·红外', value: sum('handDrawnInfrared'), color: '#9333ea' },
    {
      key: 'spectralUnspecified',
      label: '未指定光谱',
      value: sum('photoUnspecified') + sum('handDrawnUnspecified'),
      color: '#64748b',
    },
    { key: 'typeUnspecified', label: '类型未指定', value: sum('typeUnspecified'), color: '#dc2626' },
  ].map((item) => ({
    ...item,
    percent: percentage(item.value, grandTotal.value),
  }))
})

const barHeight = (value) => {
  const max = Math.max(...distribution.value.map((item) => item.value), 1)
  return `${Math.max(3, (asNumber(value) / max) * 100)}%`
}

const donutCircumference = 2 * Math.PI * 64

const donutSegments = computed(() => {
  const total = distribution.value.reduce((sum, item) => sum + item.value, 0)
  let offset = 0

  return distribution.value
    .filter((item) => item.value > 0)
    .map((item) => {
      const length = total ? (item.value / total) * donutCircumference : 0
      const segment = {
        ...item,
        dasharray: `${length} ${donutCircumference}`,
        dashoffset: `${-offset}`,
      }
      offset += length
      return segment
    })
})

const completeCount = computed(() =>
  distribution.value.slice(0, 4).reduce((sum, item) => sum + item.value, 0),
)

const unspecifiedCount = computed(() => distribution.value[4]?.value || 0)
const typeUnspecifiedCount = computed(() => distribution.value[5]?.value || 0)
const completeRatio = computed(() =>
  grandTotal.value ? completeCount.value / grandTotal.value : 0,
)

const gaugePercent = computed(() => percentage(completeCount.value, grandTotal.value))
const gaugeCircumference = 2 * Math.PI * 50
const gaugeOffset = computed(
  () => gaugeCircumference * (1 - gaugePercent.value / 100),
)

const kpiCards = computed(() => {
  const data = totals.value
  const uniqueImages = asNumber(data.unique_images)
  const sourceFiles = asNumber(data.source_files)
  const duplicates = asNumber(data.duplicates)
  const damaged = asNumber(data.damaged)
  const conflicts = asNumber(data.conflicts)
  const redundantSources = Math.max(sourceFiles - uniqueImages, 0)

  return [
    {
      key: 'unique',
      label: '唯一图片数',
      display: formatNumber(uniqueImages),
      meta: `${categoryRows.value.length} 个分类`,
      icon: 'image-multiple-outline',
      accent: '#2563eb',
    },
    {
      key: 'source',
      label: '源文件总数',
      display: formatNumber(sourceFiles),
      meta: `较唯一样本多 ${formatNumber(redundantSources)} 条来源`,
      icon: 'database-outline',
      accent: '#0f172a',
    },
    {
      key: 'duplicates',
      label: '重复文件',
      display: formatNumber(duplicates),
      meta: `占源文件 ${formatPercent(percentage(duplicates, sourceFiles))}`,
      icon: 'content-copy',
      accent: '#7c3aed',
    },
    {
      key: 'damaged',
      label: '损坏文件',
      display: formatNumber(damaged),
      meta: `占源文件 ${formatPercent(percentage(damaged, sourceFiles))}`,
      icon: 'alert-decagram-outline',
      accent: '#dc2626',
    },
    {
      key: 'conflicts',
      label: '冲突待审',
      display: formatNumber(conflicts),
      meta: `占源文件 ${formatPercent(percentage(conflicts, sourceFiles))}`,
      icon: 'scale-balance',
      accent: '#d97706',
    },
    {
      key: 'spectral',
      label: '完整光谱标注率',
      display: formatPercent(completeRatio.value * 100),
      meta: `${formatNumber(completeCount.value)} 张具备完整模态`,
      icon: 'chart-timeline-variant',
      accent: '#0891b2',
    },
  ]
})

const categoryCards = computed(() =>
  categoryRows.value.map((row) => {
    const photoTotal = row.photoVisible + row.photoInfrared + row.photoUnspecified
    const metrics = [
      { key: 'photo', label: '实拍', value: photoTotal, color: '#2563eb' },
      { key: 'handDrawn', label: '手绘', value: row.handDrawnTotal, color: '#7c3aed' },
      { key: 'visible', label: '可见光', value: row.photoVisible, color: '#0891b2' },
      { key: 'infrared', label: '红外', value: row.photoInfrared, color: '#d97706' },
    ]
    const maxMetric = Math.max(...metrics.map((metric) => metric.value), 1)

    return {
      ...row,
      metrics,
      maxMetric,
    }
  }),
)

const filteredRows = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  if (!query) return categoryRows.value

  return categoryRows.value.filter(
    (row) =>
      row.displayName.toLowerCase().includes(query) ||
      row.name.toLowerCase().includes(query),
  )
})

const miniBarHeight = (value, max) =>
  `${Math.max(4, (asNumber(value) / Math.max(asNumber(max), 1)) * 100)}%`

const loadStats = async () => {
  loading.value = true
  error.value = false
  try {
    const response = await axios.get('/api/assets/overview/stats')
    stats.value = response.data
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch (requestError) {
    error.value = true
    ElMessage.error(requestError.response?.data?.detail || '加载统计失败')
  } finally {
    loading.value = false
  }
}

const exportCsv = () => {
  const rows = filteredRows.value
  if (!rows.length) return

  const headers = [
    '类别名称',
    '类别编码',
    '实拍·可见光',
    '实拍·红外',
    '手绘·可见光',
    '手绘·红外',
    '实拍·未指定光谱',
    '手绘·未指定光谱',
    '类型未指定',
    '合计',
  ]
  const body = rows.map((row) =>
    [
      row.displayName,
      row.name,
      row.photoVisible,
      row.photoInfrared,
      row.handDrawnVisible,
      row.handDrawnInfrared,
      row.photoUnspecified,
      row.handDrawnUnspecified,
      row.typeUnspecified,
      row.total,
    ].join(','),
  )
  const csv = `\uFEFF${headers.join(',')}\n${body.join('\n')}`
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `asset-overview-${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

onMounted(loadStats)
</script>

<style scoped>
.asset-overview-page,
.asset-overview-page * {
  box-sizing: border-box;
}

.asset-overview-page {
  --surface: #f8fafc;
  --surface-low: #f1f5f9;
  --surface-mid: #f8fafc;
  --surface-high: #ffffff;
  --surface-higher: #e2e8f0;
  --border: #e2e8f0;
  --border-soft: #cbd5e1;
  --text: #0f172a;
  --text-soft: #334155;
  --muted: #64748b;
  --primary: #2563eb;
  --tertiary: #0891b2;
  --secondary: #7c3aed;
  --error: #dc2626;
  --warning: #d97706;

  min-height: calc(100vh - 104px);
  margin: -20px;
  padding: 28px;
  background:
    radial-gradient(circle at 12% -8%, rgba(37, 99, 235, 0.1), transparent 30%),
    radial-gradient(circle at 90% 0%, rgba(8, 145, 178, 0.08), transparent 26%),
    var(--surface);
  color: var(--text);
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  text-align: left;
}

.asset-overview-page h1,
.asset-overview-page h2,
.asset-overview-page h3,
.asset-overview-page p {
  margin: 0;
}

.asset-overview-page button {
  font: inherit;
}

.state-icon,
.kpi-icon,
.panel-icon,
.health-icon,
.sync-icon,
.button-icon,
.search-icon,
.category-icon {
  display: block;
  width: 1em;
  height: 1em;
  flex-shrink: 0;
}

.asset-overview-page :deep(.el-loading-mask) {
  background: rgba(248, 250, 252, 0.82);
}

.asset-overview-page :deep(.el-loading-spinner .path) {
  stroke: #2563eb;
}

.page-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.hero-copy {
  min-width: 0;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: var(--tertiary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 12px;
  letter-spacing: 0.02em;
}

.eyebrow-muted {
  color: var(--muted);
}

.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--tertiary);
  box-shadow: 0 0 0 0 rgba(8, 145, 178, 0.45);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(8, 145, 178, 0.35);
  }
  70% {
    box-shadow: 0 0 0 8px rgba(8, 145, 178, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(8, 145, 178, 0);
  }
}

.page-hero h1 {
  color: var(--text);
  font-size: 28px;
  font-weight: 600;
  line-height: 1.25;
  letter-spacing: -0.02em;
}

.page-hero p {
  margin-top: 8px;
  color: var(--muted);
  font-size: 14px;
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.sync-meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 36px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-high);
  color: var(--text-soft);
  font-size: 12px;
}

.primary-btn,
.ghost-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 36px;
  padding: 0 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease,
    opacity 0.2s ease;
}

.primary-btn {
  border: 1px solid #2563eb;
  background: #2563eb;
  color: #fff;
}

.primary-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.ghost-btn {
  border: 1px solid var(--border-soft);
  background: var(--surface-high);
  color: var(--text);
}

.ghost-btn:hover:not(:disabled) {
  border-color: #cbd5e1;
  background: var(--surface-low);
}

.primary-btn:disabled,
.ghost-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.kpi-card {
  min-height: 134px;
  padding: 16px;
  border: 1px solid var(--border);
  border-top: 2px solid var(--accent, var(--primary));
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  transition:
    background 0.2s ease,
    transform 0.2s ease;
}

.kpi-card:hover {
  background: #ffffff;
  transform: translateY(-1px);
}

.kpi-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--muted);
}

.kpi-label {
  font-size: 12px;
  line-height: 1.2;
}

.kpi-icon {
  flex-shrink: 0;
  font-size: 20px;
  color: var(--accent, var(--primary));
}

.kpi-value {
  margin-top: 16px;
  color: var(--accent, var(--text));
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 25px;
  font-weight: 600;
  line-height: 1;
}

.kpi-meta {
  margin-top: 11px;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.4;
}

.panel {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: #ffffff;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--border);
}

.panel-header h2 {
  color: var(--text);
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.panel-header p {
  margin-top: 5px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}

.panel-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.tech-chip {
  display: inline-flex;
  align-items: center;
  padding: 3px 7px;
  border-radius: 999px;
  background: #eff6ff;
  color: var(--primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 11px;
  white-space: nowrap;
}

.panel-icon {
  color: var(--tertiary);
  font-size: 22px;
}

.analytics-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(280px, 0.75fr);
  gap: 16px;
  margin-bottom: 16px;
}

.distribution-panel {
  padding-bottom: 18px;
}

.distribution-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
  gap: 14px;
  padding: 16px 20px 4px;
}

.bar-panel {
  min-width: 0;
}

.bar-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 11px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 8px;
  height: 242px;
  padding-top: 12px;
}

.bar-column {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
}

.bar-value {
  min-height: 16px;
  color: var(--text-soft);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 11px;
  white-space: nowrap;
}

.bar-track {
  display: flex;
  width: 100%;
  max-width: 64px;
  height: 170px;
  margin-top: 8px;
  align-items: flex-end;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-low);
}

.bar-fill {
  width: 100%;
  height: 0;
  border-radius: 6px 6px 0 0;
  opacity: 0.9;
  transition: height 0.35s ease;
}

.bar-label {
  margin-top: 8px;
  color: var(--text);
  font-size: 12px;
  line-height: 1.25;
  text-align: center;
}

.bar-percent {
  margin-top: 3px;
  color: var(--muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 10px;
}

.donut-panel {
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-low);
}

.donut-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  color: var(--text-soft);
  font-size: 12px;
}

.donut-heading span:last-child {
  color: var(--tertiary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 11px;
}

.donut-chart {
  position: relative;
  width: 182px;
  height: 182px;
  margin: 14px auto 12px;
}

.donut-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.donut-center {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  pointer-events: none;
  text-align: center;
}

.donut-center strong {
  color: var(--text);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 22px;
  font-weight: 600;
}

.donut-center span {
  margin-top: 3px;
  color: var(--muted);
  font-size: 11px;
}

.donut-legend {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  color: var(--muted);
  font-size: 11px;
}

.legend-dot {
  width: 8px;
  height: 8px;
  flex-shrink: 0;
  border-radius: 2px;
}

.legend-label {
  min-width: 0;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.legend-row strong {
  color: var(--text-soft);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 10px;
}

.health-panel {
  display: flex;
  flex-direction: column;
  padding-bottom: 16px;
}

.health-gauge {
  position: relative;
  width: 172px;
  height: 172px;
  margin: 18px auto 16px;
}

.gauge-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.gauge-center {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
}

.gauge-center strong {
  color: var(--text);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 24px;
  font-weight: 600;
}

.gauge-center span {
  max-width: 100px;
  margin-top: 4px;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.4;
}

.health-metrics {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0 16px;
}

.health-row {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 10px 11px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-mid);
}

.health-row span {
  min-width: 0;
  flex: 1;
  color: var(--text-soft);
  font-size: 12px;
}

.health-row strong {
  color: var(--text);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 12px;
}

.health-icon {
  font-size: 18px;
}

.health-icon.tertiary {
  color: var(--tertiary);
}

.health-icon.slate {
  color: #94a3b8;
}

.health-icon.danger {
  color: var(--error);
}

.category-matrix-panel {
  margin-bottom: 16px;
  padding-bottom: 18px;
}

.matrix-header {
  margin-bottom: 4px;
}

.category-card-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
  padding: 16px 20px 0;
}

.category-card {
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  transition:
    border-color 0.2s ease,
    background 0.2s ease,
    transform 0.2s ease;
}

.category-card:hover {
  border-color: var(--border-soft);
  background: #ffffff;
  transform: translateY(-1px);
}

.category-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}

.category-card-head h3 {
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
}

.category-card-head span {
  display: block;
  margin-top: 3px;
  color: var(--muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 10px;
}

.category-card-head strong {
  color: var(--primary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 16px;
}

.mini-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 7px;
  padding: 13px 2px 0;
}

.mini-column {
  display: flex;
  min-width: 0;
  flex: 1;
  flex-direction: column;
  align-items: center;
}

.mini-value {
  min-height: 15px;
  color: var(--text-soft);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 10px;
  white-space: nowrap;
}

.mini-track {
  display: flex;
  width: 100%;
  height: 76px;
  margin-top: 6px;
  align-items: flex-end;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 5px;
  background: var(--surface-low);
}

.mini-fill {
  width: 100%;
  height: 0;
  border-radius: 5px 5px 0 0;
  opacity: 0.88;
  transition: height 0.3s ease;
}

.mini-label {
  margin-top: 7px;
  color: var(--muted);
  font-size: 10px;
}

.category-card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding-top: 11px;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 11px;
}

.category-card-foot strong {
  color: var(--tertiary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 11px;
}

.table-panel {
  overflow: hidden;
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--border);
}

.table-toolbar h2 {
  color: var(--text);
  font-size: 17px;
  font-weight: 600;
}

.table-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  width: min(280px, 100%);
  height: 36px;
  padding: 0 11px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-mid);
  color: var(--muted);
}

.search-box:focus-within {
  border-color: var(--primary);
  color: var(--primary);
}

.search-box input {
  min-width: 0;
  flex: 1;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text);
  font-size: 12px;
}

.search-box input::placeholder {
  color: #94a3b8;
}

.compact {
  min-height: 34px;
}

.table-scroll {
  overflow-x: auto;
}

table {
  width: 100%;
  min-width: 1050px;
  border-collapse: collapse;
  font-size: 12px;
}

th,
td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: middle;
}

th {
  background: var(--surface-mid);
  color: #64748b;
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.02em;
  white-space: nowrap;
}

tbody tr {
  transition: background 0.16s ease;
}

tbody tr:hover {
  background: #f8fafc;
}

.num {
  text-align: right;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
}

.category-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 180px;
}

.category-avatar {
  display: inline-flex;
  width: 30px;
  height: 30px;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface-high);
  color: var(--primary);
}

.category-cell strong {
  display: block;
  color: var(--text);
  font-size: 12px;
  font-weight: 600;
}

.category-cell small {
  display: block;
  margin-top: 3px;
  color: var(--muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 10px;
}

.badge {
  display: inline-flex;
  min-width: 46px;
  justify-content: center;
  padding: 3px 7px;
  border-radius: 5px;
  font-size: 11px;
  line-height: 1.4;
}

.primary-badge {
  background: #eff6ff;
  color: #1d4ed8;
}

.tertiary-badge {
  background: #ecfeff;
  color: #0e7490;
}

.secondary-badge {
  background: #f5f3ff;
  color: #6d28d9;
}

.deep-secondary-badge {
  background: #f3e8ff;
  color: #7e22ce;
}

.muted-badge {
  background: #f8fafc;
  color: #475569;
}

.danger-badge {
  background: #fef2f2;
  color: #b91c1c;
}

.share-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 128px;
}

.share-track {
  height: 6px;
  flex: 1;
  overflow: hidden;
  border-radius: 999px;
  background: var(--surface-higher);
}

.share-fill {
  height: 100%;
  border-radius: inherit;
  background: var(--primary);
}

.share-cell span {
  min-width: 42px;
  color: var(--muted);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 10px;
  text-align: right;
}

.empty-cell {
  padding: 42px;
  color: var(--muted);
  text-align: center;
}

.table-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 20px;
  background: var(--surface-mid);
  color: var(--muted);
  font-size: 12px;
}

.table-summary strong {
  color: var(--text);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
}

.summary-divider {
  display: inline-block;
  width: 1px;
  height: 12px;
  margin: 0 12px;
  background: var(--border-soft);
  vertical-align: middle;
}

.summary-hint {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  color: var(--tertiary);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 11px;
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: var(--tertiary);
}

.state-panel {
  display: flex;
  min-height: calc(100vh - 104px);
  align-items: center;
  justify-content: center;
  flex-direction: column;
  text-align: center;
  color: var(--text);
}

.state-icon {
  margin-bottom: 12px;
  color: var(--error);
  font-size: 48px;
}

.state-panel h2 {
  font-size: 20px;
}

.state-panel p {
  margin: 8px 0 18px;
  color: var(--muted);
}

@media (max-width: 1280px) {
  .kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .category-card-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 980px) {
  .page-hero {
    flex-direction: column;
  }

  .hero-actions {
    justify-content: flex-start;
  }

  .analytics-grid {
    grid-template-columns: 1fr;
  }

  .distribution-layout {
    grid-template-columns: 1fr;
  }

  .category-card-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .asset-overview-page {
    padding: 18px;
  }

  .kpi-grid,
  .category-card-grid {
    grid-template-columns: 1fr;
  }

  .bar-chart {
    gap: 5px;
  }

  .table-toolbar,
  .table-summary {
    align-items: flex-start;
    flex-direction: column;
  }

  .table-actions {
    width: 100%;
    justify-content: stretch;
  }

  .search-box {
    width: 100%;
  }
}
</style>
