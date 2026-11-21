<template>
  <div v-loading="loading" class="import-records-page">
    <section class="page-hero">
      <div class="hero-copy">
        <!-- <div class="eyebrow">
          <span class="pulse-dot"></span>
          ASSET://IMPORT-RECORDS
          <span class="eyebrow-muted">· 实时导入控制台</span>
        </div> -->
        <h1>导入记录</h1>
        <!-- <p>集中跟踪扫描、策略确认、实时入库和异常重试，快速定位需要处理的资产批次。</p> -->
      </div>
      <div class="hero-actions">
        <div v-if="lastUpdated" class="sync-meta">
          <el-icon><Clock /></el-icon>
          最近刷新 {{ formatDateTime(lastUpdated) }}
        </div>
        <el-button class="ghost-button" :loading="loading" @click="loadBatches()">
          <el-icon><Refresh /></el-icon>
          刷新状态
        </el-button>
        <el-button type="primary" class="primary-button" @click="$router.push('/assets/import')">
          <el-icon><Plus /></el-icon>
          新建导入任务
        </el-button>
      </div>
    </section>

    <section class="kpi-grid" aria-label="核心指标">
      <article
        v-for="card in kpiCards"
        :key="card.key"
        class="kpi-card"
        :class="`kpi-${card.tone}`"
      >
        <span class="kpi-accent"></span>
        <div class="kpi-top">
          <span class="kpi-label">{{ card.label }}</span>
          <div class="kpi-icon">
            <el-icon><component :is="card.icon" /></el-icon>
          </div>
        </div>
        <div class="kpi-value">
          {{ card.value }}
          <span class="kpi-unit">{{ card.unit }}</span>
        </div>
        <div class="kpi-meta">{{ card.meta }}</div>
      </article>
    </section>

    <section class="workspace-card">
      <div class="workspace-toolbar">
        <div class="status-tabs" aria-label="状态筛选">
          <button
            v-for="tab in statusTabs"
            :key="tab.key"
            type="button"
            class="status-tab"
            :class="{ active: activeTab === tab.key }"
            @click="selectTab(tab.key)"
          >
            <el-icon v-if="tab.icon"><component :is="tab.icon" /></el-icon>
            <span>{{ tab.label }}</span>
            <span class="tab-count">{{ summaryFor(tab.key) }}</span>
            <span v-if="tab.key === 'confirm' && summaryFor(tab.key)" class="tab-dot"></span>
          </button>
        </div>

        <div class="toolbar-actions">
          <el-button class="ghost-button compact" @click="loadBatches()">刷新状态</el-button>
          <el-button
            type="primary"
            class="primary-button compact"
            @click="$router.push('/assets/import')"
          >
            新建导入任务
          </el-button>
        </div>
      </div>

      <div class="filter-strip">
        <div class="filter-left">
          <el-input
            v-model="filters.search"
            class="search-input"
            clearable
            placeholder="搜索批次名称、ID 或存储路径..."
            @input="onSearchInput"
            @clear="applyFilters"
            @keyup.enter="applyFilters"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-select
            v-model="filters.category"
            class="category-select"
            clearable
            placeholder="全部资产分类"
            @change="applyFilters"
          >
            <el-option
              v-for="category in categoryOptions"
              :key="category.name"
              :label="category.display_name || category.name"
              :value="category.name"
            />
          </el-select>
        </div>
        <div class="filter-right">
          <span class="auto-refresh">
            <el-icon><Clock /></el-icon>
            列表自动刷新：
            <strong>2s</strong>
          </span>
        </div>
      </div>

      <div class="table-shell">
        <el-table
          :data="batches"
          row-key="id"
          class="batch-table"
          empty-text="暂无导入任务"
          @selection-change="(rows) => (selectedRows = rows)"
        >
          <el-table-column type="selection" width="42" />
          <el-table-column label="批次 ID / 任务名称" min-width="340">
            <template #default="{ row }">
              <div class="batch-cell">
                <div class="batch-icon" :class="`icon-${statusTone(row.status)}`">
                  <el-icon><component :is="statusIcon(row.status)" /></el-icon>
                </div>
                <div class="batch-meta">
                  <div class="batch-title-row">
                    <span class="batch-title" @click="showItems(row)">
                      {{ row.batch_name || `批次 #${row.id}` }}
                    </span>
                    <span class="category-chip">{{ row.category_name }}</span>
                  </div>
                  <div class="batch-sub">
                    <span>ID: {{ row.id }}</span>
                    <span class="sep">·</span>
                    <span class="path" :title="row.image_path">{{ row.image_path }}</span>
                  </div>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="当前状态" width="150" align="center">
            <template #default="{ row }">
              <span class="status-chip" :class="`status-${statusTone(row.status)}`">
                <span class="status-dot"></span>
                {{ statusLabel(row.status) }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="导入进度 & 传输指标" min-width="260">
            <template #default="{ row }">
              <div class="progress-cell">
                <div class="progress-head">
                  <span>{{ progressLabel(row) }}</span>
                  <span :class="`progress-value-${statusTone(row.status)}`">
                    {{ progressText(row) }}
                  </span>
                </div>
                <el-progress
                  :percentage="progressFor(row)"
                  :show-text="false"
                  :stroke-width="8"
                  :color="progressColor(row)"
                />
                <div class="progress-meta">{{ progressDetail(row) }}</div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="扫描 / 入库明细" width="220" align="right">
            <template #default="{ row }">
              <div class="counts-cell">
                <div class="counts-primary">
                  {{ progressTotal(row) }}
                  <span>总数</span>
                </div>
                <div class="counts-secondary">
                  <span class="count-success">{{ importedCount(row) }} 成功</span>
                  <span class="count-sep">/</span>
                  <span class="count-warning">{{ duplicateCount(row) }} 重复</span>
                  <span class="count-sep">/</span>
                  <span class="count-danger">{{ failedCount(row) }} 失败</span>
                </div>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="流速" width="120" align="right">
            <template #default="{ row }">
              <span class="speed-value">{{ formatSpeed(row) }}</span>
            </template>
          </el-table-column>

          <el-table-column label="启动时间" width="140" align="right">
            <template #default="{ row }">
              <span class="time-value" :title="formatDateTime(row.created_at)">
                {{ formatRelativeTime(row.created_at) }}
              </span>
            </template>
          </el-table-column>

          <el-table-column label="快捷操作" width="270" align="right">
            <template #default="{ row }">
              <div class="action-group">
                <el-button link type="primary" @click="openQuality(row)">
                  <el-icon><DataLine /></el-icon>
                  体检
                </el-button>
                <el-button link @click="showItems(row)">
                  <el-icon><List /></el-icon>
                  条目
                </el-button>
                <el-button
                  v-if="canRetry(row)"
                  link
                  type="warning"
                  @click="retryBatch(row)"
                >
                  <el-icon><Refresh /></el-icon>
                  重试
                </el-button>
                <el-button
                  v-if="isActiveBatch(row)"
                  link
                  type="danger"
                  @click="stopBatch(row)"
                >
                  <el-icon><CircleClose /></el-icon>
                  停止
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pagination-bar">
        <div class="pagination-meta">
          显示第
          <strong>{{ pageStart }} - {{ pageEnd }}</strong>
          条，共
          <strong>{{ pagination.total }}</strong>
          条导入批次
        </div>
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="sizes, prev, pager, next"
          @size-change="applyFilters"
          @current-change="() => loadBatches()"
        />
      </div>
    </section>

    <el-dialog
      v-model="itemsVisible"
      class="items-dialog"
      width="78%"
      top="6vh"
      destroy-on-close
    >
      <template #header>
        <div class="dialog-header">
          <div>
            <div class="dialog-kicker">ITEM INSPECTOR · 条目透视</div>
            <h3>{{ currentBatch?.batch_name || `批次 #${currentBatch?.id}` }}</h3>
            <p>{{ currentBatch?.image_path }}</p>
          </div>
          <span
            v-if="currentBatch"
            class="status-chip"
            :class="`status-${statusTone(currentBatch.status)}`"
          >
            <span class="status-dot"></span>
            {{ statusLabel(currentBatch.status) }}
          </span>
        </div>
      </template>

      <div v-if="currentBatch" class="dialog-summary">
        <div class="dialog-stat">
          <span>总条目</span>
          <strong>{{ itemsPagination.total }}</strong>
        </div>
        <div class="dialog-stat">
          <span>已导入</span>
          <strong class="text-success">{{ importedCount(currentBatch) }}</strong>
        </div>
        <div class="dialog-stat">
          <span>重复</span>
          <strong class="text-warning">{{ duplicateCount(currentBatch) }}</strong>
        </div>
        <div class="dialog-stat">
          <span>失败</span>
          <strong class="text-danger">{{ failedCount(currentBatch) }}</strong>
        </div>
      </div>

      <el-table v-loading="itemsLoading" :data="items" class="items-table">
        <el-table-column prop="id" label="ID" width="72" />
        <el-table-column prop="source_filename" label="文件名" min-width="240" show-overflow-tooltip />
        <el-table-column prop="normalized_relative_path" label="相对路径" min-width="220" show-overflow-tooltip />
        <el-table-column label="状态" width="110" align="center">
          <template #default="{ row }">
            <span class="item-status" :class="`item-${itemStatusTone(row.status)}`">
              {{ itemStatusLabel(row.status) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="sha256" label="SHA-256" width="190" show-overflow-tooltip />
        <el-table-column prop="error_detail" label="错误详情" min-width="200" show-overflow-tooltip />
      </el-table>

      <template #footer>
        <div class="dialog-footer">
          <el-pagination
            v-model:current-page="itemsPagination.page"
            v-model:page-size="itemsPagination.page_size"
            :total="itemsPagination.total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @size-change="() => showItems(currentBatch)"
            @current-change="() => showItems(currentBatch)"
          />
          <div class="dialog-footer-actions">
            <el-button @click="itemsVisible = false">关闭检视</el-button>
            <el-button type="primary" @click="openQuality(currentBatch)">
              前往全量体检
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {
  CircleCheck,
  CircleClose,
  Clock,
  DataLine,
  InfoFilled,
  List,
  Plus,
  Refresh,
  Search,
  Warning,
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import {
  computed,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
} from 'vue'
import { useRouter } from 'vue-router'
import { getAssetCategories } from '@/services/assetImportService'

const router = useRouter()

const batches = ref([])
const loading = ref(false)
const items = ref([])
const itemsLoading = ref(false)
const itemsVisible = ref(false)
const currentBatch = ref(null)
const selectedRows = ref([])
const categories = ref([])
const lastUpdated = ref(null)

const pagination = reactive({ page: 1, page_size: 20, total: 0 })
const itemsPagination = reactive({ page: 1, page_size: 20, total: 0 })
const filters = reactive({ search: '', category: '' })
const activeTab = ref('all')

const summary = reactive({
  total: 0,
  created: 0,
  scanning: 0,
  awaiting_confirmation: 0,
  queued: 0,
  importing: 0,
  completed: 0,
  partial: 0,
  failed: 0,
  stopped: 0,
})

let pollTimer = null
let searchTimer = null

const statusTabs = [
  { key: 'all', label: '全部任务', statuses: '', icon: List },
  { key: 'confirm', label: '待确认入库', statuses: 'awaiting_confirmation', icon: Warning },
  { key: 'processing', label: '流式导入中', statuses: 'queued,importing', icon: DataLine },
  { key: 'completed', label: '已完成归档', statuses: 'completed,partial', icon: CircleCheck },
  { key: 'failed', label: '异常与失败', statuses: 'failed,stopped', icon: CircleClose },
]

const STATUS_META = {
  created: { label: '已创建', tone: 'info' },
  scanning: { label: '扫描中', tone: 'info' },
  awaiting_confirmation: { label: '待策略确认', tone: 'confirm' },
  queued: { label: '排队中', tone: 'queued' },
  importing: { label: '流式导入中', tone: 'processing' },
  completed: { label: '入库完毕', tone: 'completed' },
  partial: { label: '部分完成', tone: 'confirm' },
  failed: { label: '任务失败', tone: 'failed' },
  stopped: { label: '已停止', tone: 'stopped' },
}

const ITEM_STATUS_META = {
  pending: { label: '等待处理', tone: 'info' },
  importing: { label: '导入中', tone: 'processing' },
  imported: { label: '已导入', tone: 'completed' },
  duplicate: { label: '重复', tone: 'confirm' },
  conflict: { label: '冲突', tone: 'confirm' },
  failed: { label: '失败', tone: 'failed' },
  skipped: { label: '已跳过', tone: 'stopped' },
}

const categoryOptions = computed(() => {
  if (categories.value.length) {
    return categories.value
  }

  const names = [...new Set(batches.value.map((batch) => batch.category_name).filter(Boolean))]
  return names.map((name) => ({ name, display_name: name }))
})

const hasActiveBatches = computed(
  () => summary.queued + summary.importing > 0,
)

const pageStart = computed(() => {
  if (!pagination.total) return 0
  return (pagination.page - 1) * pagination.page_size + 1
})

const pageEnd = computed(() =>
  Math.min(pagination.page * pagination.page_size, pagination.total),
)

const activeSpeedLabel = computed(() => {
  const speeds = batches.value
    .filter((batch) => isActiveBatch(batch) && Number.isFinite(Number(batch.speed_per_second)))
    .map((batch) => Number(batch.speed_per_second))

  if (!speeds.length) return ''
  const total = speeds.reduce((sum, speed) => sum + speed, 0)
  return `${total.toFixed(1)} 张/秒`
})

const kpiCards = computed(() => {
  const active = summary.queued + summary.importing
  const completed = summary.completed + summary.partial
  const failed = summary.failed + summary.stopped

  return [
    {
      key: 'all',
      label: '全部导入批次',
      value: summary.total,
      unit: '批',
      meta: `当前筛选结果 ${pagination.total} 条`,
      tone: 'primary',
      icon: List,
    },
    {
      key: 'confirm',
      label: '策略待确认',
      value: summary.awaiting_confirmation,
      unit: '批',
      meta: '等待覆盖、命名或格式策略批复',
      tone: 'warning',
      icon: Warning,
    },
    {
      key: 'processing',
      label: '实时流式吞吐中',
      value: active,
      unit: '管道',
      meta: active ? `${activeSpeedLabel.value || '实时处理中'}` : '当前无活动摄取管道',
      tone: 'blue',
      icon: DataLine,
    },
    {
      key: 'completed',
      label: '已完成归档',
      value: completed,
      unit: '批',
      meta: `其中部分完成 ${summary.partial || 0} 批`,
      tone: 'success',
      icon: CircleCheck,
    },
    {
      key: 'failed',
      label: '异常告警批次',
      value: failed,
      unit: '批',
      meta: `失败 ${summary.failed || 0} 批 · 已停止 ${summary.stopped || 0} 批`,
      tone: 'danger',
      icon: CircleClose,
    },
  ]
})

const isActiveBatch = (batch) => ['queued', 'importing'].includes(batch?.status)

const statusMeta = (status) => STATUS_META[status] || { label: status || '未知', tone: 'info' }
const statusTone = (status) => statusMeta(status).tone
const statusLabel = (status) => statusMeta(status).label

const statusIcon = (status) => {
  const tone = statusTone(status)
  if (tone === 'processing') return DataLine
  if (tone === 'completed') return CircleCheck
  if (tone === 'failed') return CircleClose
  if (tone === 'confirm') return Warning
  if (tone === 'queued') return Clock
  return InfoFilled
}

const itemStatusMeta = (status) =>
  ITEM_STATUS_META[status] || { label: status || '未知', tone: 'info' }
const itemStatusTone = (status) => itemStatusMeta(status).tone
const itemStatusLabel = (status) => itemStatusMeta(status).label

const progressTotal = (batch) =>
  Number(
    batch?.progress_total ||
      batch?.item_total ||
      batch?.import_total ||
      batch?.scan_image_count ||
      0,
  )

const progressProcessed = (batch) =>
  Number(batch?.item_processed || batch?.import_imported || 0)

const importedCount = (batch) =>
  Number(batch?.item_imported || batch?.import_imported || 0)

const duplicateCount = (batch) =>
  Number(batch?.item_duplicate || batch?.import_duplicate || 0)

const failedCount = (batch) =>
  Number(batch?.item_failed || batch?.import_failed || 0)

const progressFor = (batch) => {
  const total = progressTotal(batch)
  const processed = progressProcessed(batch)

  if (batch?.status === 'completed') return 100
  if (total) {
    return Math.min(100, Math.round((processed / total) * 100))
  }
  if (batch?.status === 'queued') return 0

  return Number.isFinite(Number(batch?.progress_percent))
    ? Number(batch.progress_percent)
    : 0
}

const progressColor = (batch) => {
  const tone = statusTone(batch?.status)
  if (tone === 'failed') return '#F43F5E'
  if (tone === 'confirm') return '#F59E0B'
  if (tone === 'completed') return '#10B981'
  if (tone === 'stopped') return '#94A3B8'
  if (tone === 'queued') return '#64748B'
  return '#2563EB'
}

const progressLabel = (batch) => {
  switch (batch?.status) {
    case 'completed':
      return '100% 完成'
    case 'partial':
      return '部分完成'
    case 'failed':
      return '中断于'
    case 'stopped':
      return '停止于'
    case 'awaiting_confirmation':
      return '预检完成'
    case 'queued':
      return '等待分配'
    case 'importing':
      return `${progressFor(batch)}%`
    default:
      return batch?.status || '—'
  }
}

const progressText = (batch) => {
  const processed = progressProcessed(batch)
  const total = progressTotal(batch)

  switch (batch?.status) {
    case 'completed':
      return `${processed} / ${total} 全部通过`
    case 'partial':
      return `${processed} / ${total} 已入库`
    case 'failed':
      return `${processed} / ${total} 已处理`
    case 'stopped':
      return `${processed} / ${total} 已处理`
    case 'awaiting_confirmation':
      return `${batch.scan_issue_count || 0} 项待确认`
    case 'importing':
    case 'queued':
      return `${processed} / ${total} 文件`
    default:
      return '—'
  }
}

const progressDetail = (batch) => {
  const speed = formatSpeed(batch)

  switch (batch?.status) {
    case 'completed':
      return '自动标签标记已完成 · 元数据已入库'
    case 'partial':
      return `已完成主要流程，${failedCount(batch)} 项异常待处理`
    case 'failed':
      return `任务中断，${failedCount(batch)} 项失败可重试`
    case 'stopped':
      return '已安全停止，可重新加入队列续传'
    case 'awaiting_confirmation':
      return `${batch.scan_issue_count || 0} 项策略冲突等待授权`
    case 'importing':
    case 'queued':
      return speed === '—' ? '正在同步传输指标...' : `${speed} · ${progressText(batch)}`
    default:
      return '等待系统调度'
  }
}

const formatSpeed = (batch) => {
  if (!isActiveBatch(batch)) return '—'
  const speed = Number(batch?.speed_per_second)
  if (Number.isFinite(speed) && speed > 0) {
    return `${speed.toFixed(1)} 张/秒`
  }
  return '—'
}

const canRetry = (batch) =>
  ['failed', 'stopped', 'partial', 'completed'].includes(batch?.status)

const formatDateTime = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatRelativeTime = (value) => {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'

  const diff = Date.now() - date.getTime()
  const minutes = Math.floor(diff / 60000)
  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}小时前`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}天前`
  return formatDateTime(value)
}

const summaryFor = (key) => {
  if (key === 'all') return summary.total
  if (key === 'confirm') return summary.awaiting_confirmation
  if (key === 'processing') return summary.queued + summary.importing
  if (key === 'completed') return summary.completed + summary.partial
  if (key === 'failed') return summary.failed + summary.stopped
  return 0
}

const updateSummary = (data, total) => {
  summary.total = Number(total || 0)
  summary.created = Number(data?.created || 0)
  summary.scanning = Number(data?.scanning || 0)
  summary.awaiting_confirmation = Number(data?.awaiting_confirmation || 0)
  summary.queued = Number(data?.queued || 0)
  summary.importing = Number(data?.importing || 0)
  summary.completed = Number(data?.completed || 0)
  summary.partial = Number(data?.partial || 0)
  summary.failed = Number(data?.failed || 0)
  summary.stopped = Number(data?.stopped || 0)
}

const syncPolling = () => {
  if (hasActiveBatches.value && pollTimer === null) {
    pollTimer = setInterval(() => loadBatches(true), 2000)
  } else if (!hasActiveBatches.value && pollTimer !== null) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

const loadBatches = async (silent = false) => {
  if (!silent) loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    const activeStatuses = statusTabs.find((tab) => tab.key === activeTab.value)?.statuses
    if (activeStatuses) params.status = activeStatuses
    if (filters.category) params.category_name = filters.category
    if (filters.search.trim()) params.search = filters.search.trim()

    const response = await axios.get('/api/assets/imports', { params })
    batches.value = response.data.batches || []
    pagination.total = response.data.total || 0
    updateSummary(response.data.summary || {}, response.data.summary_total || 0)
    lastUpdated.value = new Date()
  } catch (error) {
    if (!silent) {
      ElMessage.error('加载导入任务失败')
    }
  } finally {
    if (!silent) loading.value = false
    syncPolling()
  }
}

const selectTab = (key) => {
  activeTab.value = key
  pagination.page = 1
  loadBatches()
}

const onSearchInput = () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(applyFilters, 320)
}

const applyFilters = () => {
  pagination.page = 1
  loadBatches()
}

const loadCategories = async () => {
  try {
    categories.value = await getAssetCategories()
  } catch {
    // The fallback in categoryOptions will derive categories from loaded batches.
  }
}

const showItems = async (batch) => {
  if (!batch) return
  const isNewBatch = currentBatch.value?.id !== batch.id
  currentBatch.value = batch
  if (isNewBatch) {
    itemsPagination.page = 1
  }
  itemsVisible.value = true
  itemsLoading.value = true
  try {
    const response = await axios.get(`/api/assets/imports/${batch.id}/items`, {
      params: {
        page: itemsPagination.page,
        page_size: itemsPagination.page_size,
      },
    })
    items.value = response.data.items || []
    itemsPagination.total = response.data.total || 0
  } catch (error) {
    ElMessage.error('加载导入条目失败')
  } finally {
    itemsLoading.value = false
  }
}

const retryBatch = async (batch) => {
  try {
    await ElMessageBox.confirm(
      `确认重新提交批次 #${batch.id} 到导入队列？`,
      '重新加入队列',
      {
        confirmButtonText: '确认重试',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  try {
    await axios.post(`/api/assets/imports/${batch.id}/retry`)
    ElMessage.success('已重新加入队列')
    loadBatches()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '重试失败')
  }
}

const stopBatch = async (batch) => {
  try {
    await ElMessageBox.confirm(
      `确认停止批次 #${batch.id} 的导入流程？`,
      '停止导入',
      {
        confirmButtonText: '停止导入',
        cancelButtonText: '取消',
        type: 'warning',
      },
    )
  } catch {
    return
  }

  try {
    await axios.post(`/api/assets/imports/${batch.id}/stop`)
    ElMessage.success('已停止')
    loadBatches()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '停止失败')
  }
}

const openQuality = (batch) => {
  if (!batch?.id) return
  router.push(`/assets/quality/${batch.id}`)
}

onMounted(() => {
  loadCategories()
  loadBatches()
})

onBeforeUnmount(() => {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
  }
  if (searchTimer) {
    clearTimeout(searchTimer)
  }
})
</script>

<style scoped>
.import-records-page {
  --primary: #2563eb;
  --primary-deep: #1d4ed8;
  --primary-soft: #eff6ff;
  --teal: #0d9488;
  --indigo: #6366f1;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #f43f5e;
  --canvas: #f8fafc;
  --surface: #ffffff;
  --surface-subtle: #f1f5f9;
  --surface-muted: #f8fafc;
  --border: #e2e8f0;
  --border-strong: #cbd5e1;
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;

  display: block;
  min-height: 100%;
  padding: 24px;
  background: var(--canvas);
  color: var(--text-primary);
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

.page-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.hero-copy {
  min-width: 0;
}

.eyebrow {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-secondary);
  font-family: ui-monospace, 'SFMono-Regular', 'Cascadia Code', Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.35);
  animation: pulse-dot 2s infinite;
}

.eyebrow-muted {
  color: var(--text-muted);
  font-weight: 500;
}

.hero-copy h1 {
  margin: 8px 0 6px;
  font-size: 30px;
  line-height: 38px;
  letter-spacing: -0.02em;
  color: var(--text-primary);
  font-weight: 750;
}

.hero-copy p {
  max-width: 760px;
  margin: 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 22px;
}

.hero-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.sync-meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 12px;
}

.ghost-button,
.primary-button {
  height: 36px;
  border-radius: 8px;
  font-weight: 600;
}

.ghost-button {
  border-color: var(--border-strong);
  color: var(--text-primary);
  background: var(--surface);
}

.ghost-button:hover,
.ghost-button:focus {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-soft);
}

.primary-button {
  border-color: var(--primary);
  background: var(--primary);
}

.primary-button:hover,
.primary-button:focus {
  border-color: var(--primary-deep);
  background: var(--primary-deep);
}

.compact {
  height: 32px;
  padding: 0 12px;
  font-size: 13px;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.kpi-card {
  position: relative;
  overflow: hidden;
  min-height: 150px;
  padding: 18px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.kpi-card:hover {
  transform: translateY(-2px);
  border-color: var(--border-strong);
  box-shadow: 0 10px 25px -12px rgba(15, 23, 42, 0.18);
}

.kpi-accent {
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: var(--primary);
}

.kpi-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.kpi-label {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.kpi-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 9px;
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 21px;
}

.kpi-value {
  margin-top: 14px;
  color: var(--text-primary);
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 30px;
  line-height: 34px;
  font-weight: 750;
  letter-spacing: -0.02em;
}

.kpi-unit {
  margin-left: 4px;
  color: var(--text-muted);
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 13px;
  font-weight: 500;
}

.kpi-meta {
  margin-top: 12px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 17px;
}

.kpi-warning .kpi-accent {
  background: var(--warning);
}

.kpi-warning .kpi-icon {
  background: #fffbeb;
  color: #b45309;
}

.kpi-blue .kpi-accent {
  background: var(--primary);
}

.kpi-blue .kpi-icon {
  background: #eff6ff;
  color: #1d4ed8;
}

.kpi-success .kpi-accent {
  background: var(--success);
}

.kpi-success .kpi-icon {
  background: #ecfdf5;
  color: #047857;
}

.kpi-danger .kpi-accent {
  background: var(--danger);
}

.kpi-danger .kpi-icon {
  background: #fff1f2;
  color: #be123c;
}

.workspace-card {
  overflow: hidden;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.workspace-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px 0;
  flex-wrap: wrap;
}

.status-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  overflow-x: auto;
  padding-bottom: 14px;
}

.status-tab {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex: 0 0 auto;
  min-height: 34px;
  padding: 6px 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--text-secondary);
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease;
}

.status-tab:hover {
  background: var(--surface-subtle);
  color: var(--text-primary);
}

.status-tab.active {
  background: #eef2ff;
  color: var(--primary-deep);
}

.tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 18px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.16);
  color: var(--text-secondary);
  font-family: ui-monospace, 'SFMono-Regular', 'Cascadia Code', Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace;
  font-size: 11px;
  font-weight: 700;
}

.status-tab.active .tab-count {
  background: rgba(37, 99, 235, 0.12);
  color: var(--primary-deep);
}

.tab-dot {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--warning);
  box-shadow: 0 0 0 2px var(--surface);
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding-bottom: 14px;
}

.filter-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 20px;
  background: var(--surface-muted);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  flex-wrap: wrap;
}

.filter-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 280px;
  flex-wrap: wrap;
}

.search-input {
  width: min(100%, 340px);
}

.category-select {
  width: 220px;
}

.filter-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.auto-refresh {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 12px;
}

.auto-refresh strong {
  color: var(--primary);
  font-family: ui-monospace, 'SFMono-Regular', 'Cascadia Code', Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace;
  font-size: 12px;
}

.table-shell {
  padding: 0 20px 8px;
}

.batch-table {
  width: 100%;
  --el-table-border-color: #edf2f7;
  --el-table-header-bg-color: #f8fafc;
  --el-table-row-hover-bg-color: #f8fafc;
  --el-table-text-color: #0f172a;
  --el-table-header-text-color: #475569;
}

.batch-table :deep(.el-table__header th.el-table__cell) {
  height: 42px;
  padding: 8px 0;
  background: #f8fafc;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border-bottom: 1px solid #cbd5e1;
}

.batch-table :deep(.el-table__body td.el-table__cell) {
  padding: 12px 0;
  vertical-align: middle;
}

.batch-table :deep(.el-table__cell) {
  padding-right: 12px;
  padding-left: 12px;
}

.batch-table :deep(.el-table__row) {
  transition: background 0.16s ease;
}

.batch-cell {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
  padding: 2px 0;
}

.batch-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  border-radius: 8px;
  font-size: 17px;
}

.batch-meta {
  min-width: 0;
  flex: 1;
}

.batch-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.batch-title {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 650;
  cursor: pointer;
  transition: color 0.16s ease;
}

.batch-title:hover {
  color: var(--primary);
}

.category-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 7px;
  border-radius: 5px;
  background: var(--surface-subtle);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.batch-sub {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  color: var(--text-muted);
  font-family: ui-monospace, 'SFMono-Regular', 'Cascadia Code', Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace;
  font-size: 11px;
}

.batch-sub .sep {
  color: var(--border-strong);
}

.batch-sub .path {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.icon-processing {
  background: #eff6ff;
  color: #1d4ed8;
}

.icon-completed {
  background: #ecfdf5;
  color: #047857;
}

.icon-failed {
  background: #fff1f2;
  color: #be123c;
}

.icon-confirm {
  background: #fffbeb;
  color: #b45309;
}

.icon-queued,
.icon-stopped,
.icon-info {
  background: #f1f5f9;
  color: #64748b;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 650;
  line-height: 18px;
  white-space: nowrap;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}

.status-processing {
  background: #eff6ff;
  color: #1d4ed8;
}

.status-processing .status-dot {
  animation: pulse-dot 1.4s infinite;
}

.status-completed {
  background: #ecfdf5;
  color: #047857;
}

.status-failed {
  background: #fff1f2;
  color: #be123c;
}

.status-confirm {
  background: #fffbeb;
  color: #b45309;
}

.status-queued,
.status-stopped,
.status-info {
  background: #f1f5f9;
  color: #64748b;
}

.progress-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--text-secondary);
  font-family: ui-monospace, 'SFMono-Regular', 'Cascadia Code', Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace;
  font-size: 11px;
  line-height: 16px;
}

.progress-head > span:last-child {
  text-align: right;
  white-space: nowrap;
}

.progress-value-processing,
.progress-value-completed {
  color: var(--primary);
}

.progress-value-completed {
  color: var(--success);
}

.progress-value-failed {
  color: var(--danger);
}

.progress-value-confirm {
  color: var(--warning);
}

.progress-value-stopped,
.progress-value-queued,
.progress-value-info {
  color: var(--text-muted);
}

.progress-meta {
  color: var(--text-muted);
  font-size: 11px;
  line-height: 16px;
}

.counts-cell {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.counts-primary {
  color: var(--text-primary);
  font-family: ui-monospace, 'SFMono-Regular', 'Cascadia Code', Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace;
  font-size: 14px;
  font-weight: 750;
}

.counts-primary span {
  margin-left: 4px;
  color: var(--text-muted);
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
  font-size: 11px;
  font-weight: 500;
}

.counts-secondary {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
  font-size: 11px;
}

.count-sep {
  color: var(--border-strong);
}

.count-success {
  color: var(--success);
}

.count-warning {
  color: var(--warning);
}

.count-danger {
  color: var(--danger);
}

.speed-value {
  color: var(--primary);
  font-family: ui-monospace, 'SFMono-Regular', 'Cascadia Code', Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace;
  font-size: 13px;
  font-weight: 650;
}

.time-value {
  color: var(--text-muted);
  font-size: 12px;
  white-space: nowrap;
}

.action-group {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 2px;
}

.action-group .el-button {
  height: 30px;
  margin-left: 0;
  padding: 0 7px;
  font-size: 12px;
  font-weight: 600;
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 20px;
  background: var(--surface-muted);
  border-top: 1px solid var(--border);
  flex-wrap: wrap;
}

.pagination-meta {
  color: var(--text-secondary);
  font-size: 12px;
}

.pagination-meta strong {
  color: var(--text-primary);
  font-family: ui-monospace, 'SFMono-Regular', 'Cascadia Code', Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace;
  font-size: 12px;
}

.items-dialog :deep(.el-dialog) {
  overflow: hidden;
  border-radius: 12px;
  box-shadow: 0 24px 60px -18px rgba(15, 23, 42, 0.3);
}

.items-dialog :deep(.el-dialog__header) {
  margin: 0;
  padding: 18px 22px;
  background: #f8fafc;
  border-bottom: 1px solid var(--border);
}

.items-dialog :deep(.el-dialog__body) {
  padding: 20px 22px;
}

.items-dialog :deep(.el-dialog__footer) {
  padding: 14px 22px;
  background: #f8fafc;
  border-top: 1px solid var(--border);
}

.dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.dialog-kicker {
  color: var(--primary);
  font-family: ui-monospace, 'SFMono-Regular', 'Cascadia Code', Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.dialog-header h3 {
  margin: 4px 0 4px;
  color: var(--text-primary);
  font-size: 20px;
  line-height: 26px;
}

.dialog-header p {
  margin: 0;
  color: var(--text-muted);
  font-family: ui-monospace, 'SFMono-Regular', 'Cascadia Code', Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace;
  font-size: 12px;
}

.dialog-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.dialog-stat {
  padding: 12px 14px;
  background: var(--surface-muted);
  border: 1px solid var(--border);
  border-radius: 9px;
}

.dialog-stat span {
  display: block;
  color: var(--text-muted);
  font-size: 11px;
}

.dialog-stat strong {
  display: block;
  margin-top: 4px;
  color: var(--text-primary);
  font-family: ui-monospace, 'SFMono-Regular', 'Cascadia Code', Consolas, 'Liberation Mono', 'DejaVu Sans Mono', monospace;
  font-size: 20px;
  line-height: 26px;
}

.text-success {
  color: var(--success);
}

.text-warning {
  color: var(--warning);
}

.text-danger {
  color: var(--danger);
}

.items-table {
  --el-table-border-color: #edf2f7;
  --el-table-header-bg-color: #f8fafc;
  --el-table-header-text-color: #475569;
  --el-table-row-hover-bg-color: #f8fafc;
}

.items-table :deep(.el-table__header th.el-table__cell) {
  background: #f8fafc;
  color: #475569;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.item-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 650;
}

.item-completed {
  background: #ecfdf5;
  color: #047857;
}

.item-processing {
  background: #eff6ff;
  color: #1d4ed8;
}

.item-failed {
  background: #fff1f2;
  color: #be123c;
}

.item-confirm {
  background: #fffbeb;
  color: #b45309;
}

.item-stopped,
.item-info {
  background: #f1f5f9;
  color: #64748b;
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.dialog-footer-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@keyframes pulse-dot {
  0% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.35);
  }
  70% {
    box-shadow: 0 0 0 7px rgba(16, 185, 129, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0);
  }
}

@media (max-width: 1280px) {
  .kpi-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 820px) {
  .import-records-page {
    padding: 16px;
  }

  .page-hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .kpi-grid {
    grid-template-columns: 1fr;
  }

  .workspace-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-actions {
    justify-content: flex-end;
  }

  .filter-strip {
    align-items: stretch;
  }

  .filter-left {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input,
  .category-select {
    width: 100%;
  }

  .pagination-bar,
  .dialog-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
