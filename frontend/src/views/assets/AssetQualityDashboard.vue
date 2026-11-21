<template>
  <div class="quality-page">
    <section class="panel hero-panel">
      <header class="hero-header">
        <div class="hero-copy">
          <!-- <div class="eyebrow-row">
            <span class="eyebrow-tag">
              <i class="status-dot"></i>
              PRE-INGEST QA
            </span>
            <span class="eyebrow-caption">CANDIDATE-ONLY · 不触发正式入库</span>
          </div> -->

          <div class="title-row">
            <h1>入库前质量检查</h1>
            <!-- <span class="batch-chip">批次 {{ batchId }}</span> -->
          </div>

          <p class="hero-desc">{{ heroDescription }}</p>
        </div>

        <div class="hero-toolbar">
          <div class="profile-control">
            <span class="control-label">画像规范</span>
            <el-select
              v-model="selectedProfileKey"
              clearable
              placeholder="全部画像"
              class="profile-select"
              @change="onProfileChange"
            >
              <el-option
                v-for="profile in profiles"
                :key="profile.profile_key"
                :label="profile.profile_key"
                :value="profile.profile_key"
              />
            </el-select>
          </div>
          <el-button type="primary" :loading="creatingJob" @click="startJob">
            开始检查
          </el-button>
          <el-button :loading="loading" @click="loadAll">刷新</el-button>
        </div>
      </header>

      <div v-if="job" class="job-strip">
        <div class="job-strip-top">
          <div class="job-identity">
            <span class="job-state" :class="`is-${job.state}`">
              <i class="status-dot"></i>
              {{ jobStateLabel }}
            </span>
            <span class="job-meta">
              候选资产：
              <strong class="job-count">{{ jobProcessed }} / {{ jobTotal }}</strong>
            </span>
          </div>
          <el-progress
            :percentage="jobPercent"
            :stroke-width="8"
            class="job-progress"
          />
        </div>

        <template v-if="previewSegments.length">
          <div class="segmented-progress" aria-label="质量建议分布">
            <span
              v-for="segment in previewSegments"
              :key="segment.key"
              :class="`is-${segment.key}`"
              :style="{ width: `${segment.percent}%` }"
              :title="`${segment.label} ${segment.value} 张 · ${segment.percent}%`"
            ></span>
          </div>
          <div class="progress-legend">
            <span v-for="segment in previewSegments" :key="segment.key" class="legend-item">
              <i :class="`legend-dot is-${segment.key}`"></i>
              {{ segment.label }}
              <strong>{{ segment.value }}</strong>
              <em>{{ segment.percent }}%</em>
            </span>
          </div>
        </template>
      </div>

      <div v-if="preview" class="summary-grid">
        <article class="summary-card admit">
          <div class="summary-card-top">
            <span class="summary-label"><i class="summary-dot"></i>建议入库</span>
            <span class="summary-percent">{{ summaryPercent('admit') }}</span>
          </div>
          <div class="summary-value">{{ preview.counts.admit }}</div>
          <div class="summary-foot">无需人工介入直接归档</div>
        </article>

        <button
          type="button"
          class="summary-card review selectable"
          :class="{ selected: selectedRecommendation === 'review' }"
          :aria-pressed="selectedRecommendation === 'review'"
          @click="showCandidates('review')"
        >
          <span v-if="selectedRecommendation === 'review'" class="active-badge">当前查看</span>
          <span class="summary-card-top">
            <span class="summary-label"><i class="summary-dot"></i>建议复核</span>
            <span class="summary-percent">{{ summaryPercent('review') }}</span>
          </span>
          <span class="summary-value">{{ preview.counts.review }}</span>
          <span class="summary-foot">触发阈值偏离，需抽样或强制放行</span>
        </button>

        <button
          type="button"
          class="summary-card exclude selectable"
          :class="{ selected: selectedRecommendation === 'exclude' }"
          :aria-pressed="selectedRecommendation === 'exclude'"
          @click="showCandidates('exclude')"
        >
          <span v-if="selectedRecommendation === 'exclude'" class="active-badge">当前查看</span>
          <span class="summary-card-top">
            <span class="summary-label"><i class="summary-dot"></i>建议排除</span>
            <span class="summary-percent">{{ summaryPercent('exclude') }}</span>
          </span>
          <span class="summary-value">{{ preview.counts.exclude }}</span>
          <span class="summary-foot">损坏、重度偏离或独立检查命中</span>
        </button>

        <article class="summary-card total">
          <div class="summary-card-top">
            <span class="summary-label"><i class="summary-dot"></i>已评估</span>
            <span class="summary-percent">100%</span>
          </div>
          <div class="summary-value">{{ preview.evaluated_count }}</div>
          <div class="summary-foot">当前候选集已完成收敛</div>
        </article>
      </div>

      <el-alert
        v-if="exclusionExplanation"
        class="exclusion-note"
        :title="exclusionExplanation"
        type="info"
        :closable="false"
        show-icon
      />

      <div class="action-row">
        <el-button
          type="primary"
          :disabled="!preview || previewLoading || !preview.evaluated_count"
          @click="freezeEvaluation"
        >
          固定评估快照
        </el-button>
        <el-button
          v-if="evaluation"
          :disabled="exportState === 'processing'"
          @click="requestExport"
        >
          {{ exportState === 'completed' ? '重新导出' : '导出 CSV' }}
        </el-button>
        <a
          v-if="exportState === 'completed'"
          class="download-link"
          @click.prevent="downloadExport"
        >
          下载 CSV
        </a>
      </div>
    </section>

    <section class="panel metrics-panel">
      <header class="section-header">
        <div class="section-copy">
          <h2>指标量化分布与动态阈值干预</h2>
          <p>拖动阈值参考线或切换指标开关，实时重构判定矩阵。</p>
        </div>
        <span v-if="selectedProfileKey" class="section-pill">
          当前画像：{{ selectedProfileKey }}
        </span>
      </header>

      <div v-loading="loading" class="metrics-grid">
        <MetricHistogramCard
          v-for="item in metricCards"
          :key="item.metric.metric_id"
          :metric="item.metric"
          :histogram="item.histogram"
          :thresholds="thresholdFor(item.metric.metric_id)"
          :min-bound="item.min"
          :max-bound="item.max"
          :step="item.step"
          @threshold-change="onThresholdChange"
        />
      </div>
    </section>

    <section v-if="selectedRecommendation" class="panel candidates-panel">
      <header class="section-header candidate-header">
        <div class="candidate-title-group">
          <i class="summary-dot" :class="`is-${selectedRecommendation}`"></i>
          <div class="section-copy">
            <h2>{{ candidatePanelTitle }}</h2>
            <p>按文件、类型、量化指标与触发原因进行人工复核。</p>
          </div>
          <span class="candidate-count">{{ candidateTotal }} 张候选</span>
        </div>
        <div class="candidate-actions">
          <el-pagination
            v-model:current-page="candidatePage"
            v-model:page-size="candidatePageSize"
            :total="candidateTotal"
            layout="total, prev, pager, next"
            @current-change="onCandidatePageChange"
          />
          <el-button @click="hideCandidates">收起</el-button>
        </div>
      </header>

      <div class="candidate-body">
        <el-empty
          v-if="!previewLoading && !candidateTotal"
          description="暂无该类图片"
        />
        <el-table
          v-else
          v-loading="previewLoading"
          :data="candidates"
          class="candidate-table"
        >
          <el-table-column label="预览" width="84">
            <template #default="{ row }">
              <img
                v-if="row.decode_status === 'ok' && thumbnailUrls[row.candidate_id]"
                :src="thumbnailUrls[row.candidate_id]"
                :alt="row.source_filename"
                class="candidate-thumb"
                :class="{ 'is-loading': imagePreviewLoadingId === row.candidate_id }"
                :title="imagePreviewLoadingId === row.candidate_id ? '正在加载大图' : '点击放大'"
                @click="openImagePreview(row)"
              />
              <span v-else-if="row.decode_status === 'ok'" class="thumb-placeholder">
                {{ failedThumbnailIds[row.candidate_id] ? '预览失败' : '加载中' }}
              </span>
              <span v-else class="thumb-placeholder is-broken">损坏</span>
            </template>
          </el-table-column>
          <el-table-column
            prop="source_filename"
            label="文件名"
            min-width="180"
            show-overflow-tooltip
          />
          <el-table-column prop="category" label="类别" width="90" />
          <el-table-column label="类型" width="130">
            <template #default="{ row }">
              {{ row.capture_type || '未指定' }} / {{ row.spectral_type || '未指定' }}
            </template>
          </el-table-column>
          <el-table-column label="位深" prop="bit_depth" width="70" />
          <el-table-column label="模糊度" width="96" align="right">
            <template #default="{ row }">
              <span
                class="metric-cell"
                :class="metricCellClass('blur_effect', row.metrics?.blur_effect)"
              >{{ formatMetric(row.metrics?.blur_effect) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="对比度" width="96" align="right">
            <template #default="{ row }">
              <span
                class="metric-cell"
                :class="metricCellClass('rms_contrast', row.metrics?.rms_contrast)"
              >{{ formatMetric(row.metrics?.rms_contrast) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="噪声" width="96" align="right">
            <template #default="{ row }">
              <span
                class="metric-cell"
                :class="metricCellClass('noise_sigma', row.metrics?.noise_sigma)"
              >{{ formatMetric(row.metrics?.noise_sigma) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="过曝比例" width="104" align="right">
            <template #default="{ row }">
              <span
                class="metric-cell"
                :class="metricCellClass('bright_fraction', row.metrics?.bright_fraction)"
              >{{ formatMetric(row.metrics?.bright_fraction) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="建议" width="92">
            <template #default="{ row }">
              <span class="recommendation-chip" :class="`is-${row.recommendation}`">
                <i class="status-dot"></i>
                {{ recommendationText(row.recommendation) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="原因" min-width="200">
            <template #default="{ row }">
              <span class="reason-text">{{ reasonText(row) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <ElImageViewer
      v-if="previewImageUrl"
      :url-list="[previewImageUrl]"
      @close="closeImagePreview"
    />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElImageViewer, ElMessage } from 'element-plus'
import MetricHistogramCard from '@/components/asset-quality/MetricHistogramCard.vue'
import {
  createQualityEvaluation,
  createQualityExport,
  createQualityJob,
  evaluateQualityPreview,
  getQualityExport,
  getQualityJob,
  getQualityMetrics,
  getQualityProfiles,
  downloadQualityExport,
  getQualityCandidateImage,
} from '@/services/assetQualityService'

const props = defineProps({
  batchId: { type: [String, Number], required: true },
})

const loading = ref(false)
const creatingJob = ref(false)
const job = ref(null)
const profiles = ref([])
const selectedProfileKey = ref('')
const metrics = ref(null)
const noiseMaxBound = ref(100)
const candidates = ref([])
const candidateTotal = ref(0)
const candidatePage = ref(1)
const candidatePageSize = ref(20)
const selectedRecommendation = ref('')
const thumbnailUrls = ref({})
const failedThumbnailIds = ref({})
const previewImageUrl = ref('')
const imagePreviewLoadingId = ref(null)
const preview = ref(null)
const previewLoading = ref(false)
const draftRules = ref({})
const evaluation = ref(null)
const exportState = ref('')
const exportId = ref(null)

let jobTimer = null
let previewTimer = null
let previewRevision = 0
let thumbnailRevision = 0
let imagePreviewRevision = 0
let loadedProfileKey = null

const metricCards = computed(() => {
  if (!metrics.value) return []
  return metrics.value.histograms.map((histogram) => {
    const definition = metrics.value.metric_definitions[histogram.metric_id]
    return {
      metric: { ...definition, metric_id: histogram.metric_id },
      histogram: {
        ...histogram.histogram,
        value_count: histogram.value_count,
        missing_count: histogram.missing_count,
      },
      min: metricMin(histogram.metric_id),
      max: metricMax(histogram.metric_id),
      step: metricStep(histogram.metric_id),
    }
  })
})

const heroDescription = computed(() => {
  if (selectedProfileKey.value) {
    return `批次 ${props.batchId} · 当前使用「${selectedProfileKey.value}」画像；阈值调整仅影响本次预览，可固定为评估快照。`
  }
  return '批次 ' + props.batchId + ' · 全部画像：未调整的指标按图片画像评估；滑块调整会覆盖整个批次的对应阈值。'
})

const exclusionExplanation = computed(() => {
  const exact = preview.value?.flag_counts?.EXACT_DUPLICATE || 0
  const decode = preview.value?.flag_counts?.DECODE_FAILED || 0
  if (!exact && !decode) return ''
  return `关闭四项质量指标不会关闭独立的入库检查：完全重复 ${exact} 张，解码失败 ${decode} 张；这些图片仍建议排除。`
})

const jobTotal = computed(() => {
  return job.value?.candidate_progress?.total || job.value?.total_count || 0
})

const jobProcessed = computed(() => {
  return (job.value?.candidate_progress?.completed || 0)
    + (job.value?.candidate_progress?.failed || 0)
})

const jobPercent = computed(() => {
  const total = jobTotal.value
  if (!total) return 0
  return Math.min(100, Math.round((jobProcessed.value / total) * 100))
})

const jobStateLabel = computed(() => {
  const labels = {
    pending: '待处理',
    processing: '检查中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消',
  }
  return labels[job.value?.state] || job.value?.state || '—'
})

const previewSegments = computed(() => {
  const counts = preview.value?.counts || {}
  const total = preview.value?.evaluated_count || 0
  if (!total) return []

  const definitions = [
    { key: 'admit', label: '建议入库', value: Number(counts.admit) || 0 },
    { key: 'review', label: '建议复核', value: Number(counts.review) || 0 },
    { key: 'exclude', label: '建议排除', value: Number(counts.exclude) || 0 },
  ]

  return definitions
    .map((item) => ({
      ...item,
      percent: Math.round((item.value / total) * 1000) / 10,
    }))
    .filter((item) => item.value > 0)
})

const candidatePanelTitle = computed(() => {
  return selectedRecommendation.value === 'review'
    ? '建议复核的图片清单'
    : '建议排除的图片清单'
})

function metricMin(metricId) {
  return 0
}

function metricMax(metricId) {
  if (metricId === 'noise_sigma') return noiseMaxBound.value
  return 1
}

function metricStep(metricId) {
  if (metricId === 'noise_sigma') return 1
  return 0.01
}

function summaryPercent(key) {
  const counts = preview.value?.counts || {}
  const total = preview.value?.evaluated_count || 0
  if (!total) return '0%'
  return `${Math.round(((Number(counts[key]) || 0) / total) * 100)}%`
}

function metricCellClass(metricId, value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) {
    return 'is-muted'
  }

  const thresholds = thresholdFor(metricId)
  if (!thresholds.enabled) return ''

  const numericValue = Number(value)
  const metric = metrics.value?.metric_definitions?.[metricId]
  const direction = metric?.direction || 'high'
  const review = Number(thresholds.review)
  const severe = Number(thresholds.severe)

  if (direction === 'high') {
    if (thresholds.severe_enabled && numericValue >= severe) return 'is-danger'
    if (numericValue >= review) return 'is-warning'
    return ''
  }

  if (thresholds.severe_enabled && numericValue <= severe) return 'is-danger'
  if (numericValue <= review) return 'is-warning'
  return ''
}

function thresholdFor(metricId) {
  const config = draftRules.value[metricId] || {}
  const defaults = {
    blur_effect: { review: 0.55, severe: 0.85 },
    rms_contrast: { review: 0.08, severe: 0.03 },
    noise_sigma: { review: 20, severe: 50 },
    bright_fraction: { review: 0.2, severe: 0.5 },
  }[metricId] || {}
  return {
    enabled: config.enabled ?? true,
    severe_enabled: config.severe_enabled ?? false,
    review: config.review ?? defaults.review,
    severe: config.severe ?? defaults.severe,
  }
}

function onThresholdChange(payload) {
  draftRules.value[payload.metric_id] = payload
  invalidatePreview(true)
  if (previewTimer) clearTimeout(previewTimer)
  previewTimer = setTimeout(loadPreview, 350)
}

function invalidatePreview(resetEvaluation = false) {
  previewRevision += 1
  preview.value = null
  candidates.value = []
  clearThumbnails()
  candidateTotal.value = 0
  previewLoading.value = true
  if (resetEvaluation) {
    evaluation.value = null
    exportState.value = ''
    exportId.value = null
  }
}

function reasonText(row) {
  const reasons = {
    DECODE_FAILED: '图片解码失败',
    BLUR_SUSPECT: '疑似模糊',
    LOW_CONTRAST: '对比度偏低',
    HIGH_NOISE: '噪声偏高',
    HIGHLIGHT_CLIPPING: '高亮像素占比偏高',
    METRIC_UNAVAILABLE: '指标缺失',
    SOURCE_CHANGED: '源文件已变化',
  }
  return (row.flags || []).map((flag) => {
    if (flag === 'EXACT_DUPLICATE') {
      if (row.duplicate_scope === 'batch') return '本批次文件完全重复'
      if (row.duplicate_scope === 'both') return '与已入库及本批次图片完全重复'
      return '与已入库图片完全重复'
    }
    return reasons[flag] || flag
  }).join('；') || '—'
}

async function onProfileChange() {
  candidatePage.value = 1
  invalidatePreview(true)
  await loadAll()
}

async function onCandidatePageChange() {
  candidates.value = []
  clearThumbnails()
  await loadPreview()
}

async function showCandidates(recommendation) {
  if (selectedRecommendation.value === recommendation) return
  selectedRecommendation.value = recommendation
  candidatePage.value = 1
  candidates.value = []
  clearThumbnails()
  candidateTotal.value = 0
  await loadPreview()
}

function hideCandidates() {
  const needsSummaryRefresh = previewLoading.value || !preview.value
  previewRevision += 1
  imagePreviewRevision += 1
  imagePreviewLoadingId.value = null
  closeImagePreview()
  selectedRecommendation.value = ''
  candidates.value = []
  clearThumbnails()
  candidateTotal.value = 0
  previewLoading.value = false
  if (needsSummaryRefresh) loadPreview()
}

async function startJob() {
  creatingJob.value = true
  try {
    const result = await createQualityJob(props.batchId)
    ElMessage.success(`已创建检查任务 ${result.job_id}`)
    await loadJob(result.job_id)
    syncJobPolling()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创建检查任务失败')
  } finally {
    creatingJob.value = false
  }
}

async function loadJob(jobId) {
  try {
    job.value = await getQualityJob(jobId)
  } catch (error) {
    ElMessage.error('加载任务状态失败')
  }
}

function syncJobPolling() {
  if (!job.value || !['pending', 'processing'].includes(job.value.state)) return
  if (jobTimer) clearInterval(jobTimer)
  jobTimer = setInterval(async () => {
    await loadJob(job.value.id)
    if (['completed', 'failed', 'cancelled'].includes(job.value.state)) {
      clearInterval(jobTimer)
      jobTimer = null
      await loadAll()
    }
  }, 1500)
}

async function loadProfiles() {
  const response = await getQualityProfiles()
  profiles.value = response.profiles || []
  const current = profiles.value.find(
    (profile) => profile.profile_key === selectedProfileKey.value,
  )
  if (loadedProfileKey !== selectedProfileKey.value) {
    draftRules.value = Object.fromEntries(
      Object.entries(current?.config?.metrics || {}).filter(([metricId]) =>
        ['blur_effect', 'rms_contrast', 'noise_sigma', 'bright_fraction'].includes(metricId),
      ),
    )
    loadedProfileKey = selectedProfileKey.value
  }
}

async function loadMetrics() {
  metrics.value = await getQualityMetrics(props.batchId, selectedProfileKey.value || null)
  const noiseHistogram = metrics.value.histograms.find((item) => item.metric_id === 'noise_sigma')
  noiseMaxBound.value = Math.max(
    100,
    Math.ceil(noiseHistogram?.histogram.edges.at(-1) ?? 0),
    Math.ceil(draftRules.value.noise_sigma?.review ?? 0),
    Math.ceil(draftRules.value.noise_sigma?.severe ?? 0),
  )
}

async function loadPreview() {
  const revision = ++previewRevision
  previewLoading.value = true
  try {
    const response = await evaluateQualityPreview(props.batchId, {
      request_id: `ui-${revision}`,
      profile_key: selectedProfileKey.value || undefined,
      draft_rules: draftRules.value,
      recommendation_filter: selectedRecommendation.value || undefined,
      page: candidatePage.value,
      page_size: candidatePageSize.value,
    })
    if (revision !== previewRevision) return
    preview.value = response
    clearThumbnails()
    candidates.value = response.candidate_items || []
    candidateTotal.value = response.candidate_total || 0
    candidatePage.value = response.page || 1
    loadThumbnails(candidates.value)
  } catch (error) {
    if (revision === previewRevision) {
      ElMessage.error(error.response?.data?.detail || '加载评估预览失败')
    }
  } finally {
    if (revision === previewRevision) previewLoading.value = false
  }
}

async function loadAll() {
  loading.value = true
  invalidatePreview()
  try {
    await loadProfiles()
    await loadMetrics()
    await loadPreview()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载质量数据失败')
    previewLoading.value = false
  } finally {
    loading.value = false
  }
}

async function freezeEvaluation() {
  try {
    const result = await createQualityEvaluation(props.batchId, {
      profile_key: selectedProfileKey.value || undefined,
      draft_rules: draftRules.value,
    })
    evaluation.value = { id: result.evaluation_id }
    exportState.value = ''
    exportId.value = null
    ElMessage.success(`评估快照已固定：${result.evaluation_id}`)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '固定评估快照失败')
  }
}

async function requestExport() {
  if (!evaluation.value) return
  try {
    const result = await createQualityExport(evaluation.value.id)
    exportId.value = result.export_id
    exportState.value = 'pending'
    pollExport()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创建导出任务失败')
  }
}

async function pollExport() {
  if (!exportId.value) return
  const current = await getQualityExport(exportId.value)
  exportState.value = current.state
  if (['completed', 'failed'].includes(current.state)) {
    if (current.state === 'completed') {
      ElMessage.success(`CSV 已生成，共 ${current.row_count} 行`)
    } else {
      ElMessage.error(current.error || '导出失败')
    }
    return
  }
  setTimeout(pollExport, 1200)
}

async function downloadExport() {
  if (!exportId.value) return
  try {
    const response = await downloadQualityExport(exportId.value)
    const contentDisposition = response.headers?.['content-disposition'] || ''
    const fallbackName = `quality-export-${exportId.value}.csv`
    const filename = parseDownloadFilename(contentDisposition) || fallbackName
    const blobUrl = window.URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(blobUrl)
  } catch (error) {
    ElMessage.error('下载 CSV 失败')
  }
}

function parseDownloadFilename(contentDisposition) {
  const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      return utf8Match[1]
    }
  }
  const plainMatch = contentDisposition.match(/filename="?([^";]+)"?/i)
  return plainMatch?.[1] || ''
}

function clearThumbnails() {
  thumbnailRevision += 1
  Object.values(thumbnailUrls.value).forEach((url) => URL.revokeObjectURL(url))
  thumbnailUrls.value = {}
  failedThumbnailIds.value = {}
}

function loadThumbnails(items) {
  const revision = thumbnailRevision
  items.filter((item) => item.decode_status === 'ok').forEach(async (item) => {
    try {
      const url = await getQualityCandidateImage(item.candidate_id)
      if (revision !== thumbnailRevision) {
        URL.revokeObjectURL(url)
        return
      }
      thumbnailUrls.value[item.candidate_id] = url
    } catch (error) {
      if (revision === thumbnailRevision) failedThumbnailIds.value[item.candidate_id] = true
    }
  })
}

async function openImagePreview(row) {
  if (imagePreviewLoadingId.value === row.candidate_id) return
  const revision = ++imagePreviewRevision
  imagePreviewLoadingId.value = row.candidate_id
  try {
    const url = await getQualityCandidateImage(row.candidate_id, 1600)
    if (revision !== imagePreviewRevision) {
      URL.revokeObjectURL(url)
      return
    }
    closeImagePreview()
    previewImageUrl.value = url
  } catch (error) {
    if (revision === imagePreviewRevision) ElMessage.error('加载放大图片失败')
  } finally {
    if (revision === imagePreviewRevision) imagePreviewLoadingId.value = null
  }
}

function closeImagePreview() {
  if (previewImageUrl.value) URL.revokeObjectURL(previewImageUrl.value)
  previewImageUrl.value = ''
}

function formatMetric(value) {
  if (value === null || value === undefined) return '—'
  return Number(value).toFixed(3)
}

function recommendationText(recommendation) {
  if (recommendation === 'admit') return '入库'
  if (recommendation === 'review') return '复核'
  return '排除'
}

onMounted(async () => {
  await loadAll()
})

onBeforeUnmount(() => {
  previewRevision += 1
  thumbnailRevision += 1
  imagePreviewRevision += 1
  clearThumbnails()
  closeImagePreview()
  if (jobTimer) clearInterval(jobTimer)
  if (previewTimer) clearTimeout(previewTimer)
})
</script>

<style scoped>
.quality-page {
  --canvas-bg: #f8fafc;
  --surface-card: #ffffff;
  --surface-subtle: #f1f5f9;
  --surface-container: #eff6ff;
  --border-subtle: #e2e8f0;
  --border-strong: #cbd5e1;
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
  --primary: #2563eb;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #f43f5e;
  --font-sans: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  --font-display: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  --el-color-primary: var(--primary);
  --el-color-success: var(--success);
  --el-color-warning: var(--warning);
  --el-color-danger: var(--danger);
  --el-border-radius-base: 8px;

  min-height: 100%;
  padding: 24px;
  background: var(--canvas-bg);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 13px;
  line-height: 1.5;
}

.panel {
  margin-bottom: 16px;
  overflow: hidden;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--surface-card);
  box-shadow: 0 1px 2px 0 rgba(15, 23, 42, 0.04);
}

.hero-panel {
  padding: 20px;
}

.hero-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}

.hero-copy {
  min-width: 0;
}

.eyebrow-row,
.title-row,
.job-identity,
.candidate-title-group {
  display: flex;
  align-items: center;
}

.eyebrow-row {
  gap: 10px;
  flex-wrap: wrap;
}

.eyebrow-tag,
.batch-chip,
.section-pill,
.candidate-count {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #1d4ed8;
  background: var(--surface-container);
  border: 1px solid #dbeafe;
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  line-height: 16px;
  white-space: nowrap;
}

.eyebrow-tag {
  padding: 3px 8px;
}

.eyebrow-caption {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.03em;
}

.title-row {
  gap: 12px;
  margin-top: 10px;
}

.title-row h1,
.section-copy h2 {
  margin: 0;
  color: var(--text-primary);
  font-family: var(--font-display);
  font-weight: 700;
  letter-spacing: -0.01em;
}

.title-row h1 {
  font-size: 24px;
  line-height: 32px;
}

.batch-chip {
  padding: 3px 8px;
  color: var(--primary);
}

.hero-desc,
.section-copy p {
  margin: 7px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 18px;
}

.hero-desc {
  max-width: 780px;
}

.hero-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.profile-control {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  background: var(--surface-card);
}

.control-label {
  color: var(--text-muted);
  font-size: 11px;
  white-space: nowrap;
}

.profile-select {
  width: 220px;
}

.hero-toolbar :deep(.el-select__wrapper) {
  min-height: 28px;
  padding: 0 6px;
  border: 0;
  box-shadow: none;
  background: transparent;
}

.hero-toolbar :deep(.el-button) {
  min-height: 34px;
  border-radius: 8px;
  font-weight: 500;
}

.hero-toolbar :deep(.el-button--primary) {
  box-shadow: 0 1px 2px rgba(37, 99, 235, 0.18);
}

.job-strip {
  margin-top: 18px;
  padding: 14px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: #f8fafc;
}

.job-strip-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
}

.job-identity {
  gap: 12px;
  flex-wrap: wrap;
}

.job-state,
.recommendation-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.status-dot {
  width: 7px;
  height: 7px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: var(--text-muted);
}

.job-state.is-pending {
  color: #64748b;
  background: #f1f5f9;
}

.job-state.is-processing {
  color: #1d4ed8;
  background: #eff6ff;
}

.job-state.is-processing .status-dot {
  background: var(--primary);
  animation: status-pulse 1.2s ease-in-out infinite;
}

.job-state.is-completed {
  color: #047857;
  background: #ecfdf5;
}

.job-state.is-completed .status-dot {
  background: var(--success);
}

.job-state.is-failed {
  color: #be123c;
  background: #fff1f2;
}

.job-state.is-failed .status-dot {
  background: var(--danger);
}

.job-state.is-cancelled {
  color: #475569;
  background: #f1f5f9;
}

.job-meta {
  color: var(--text-secondary);
  font-size: 12px;
}

.job-count {
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-weight: 700;
}

.job-progress {
  width: 320px;
  max-width: 100%;
}

.segmented-progress {
  display: flex;
  height: 8px;
  margin-top: 12px;
  overflow: hidden;
  border-radius: 999px;
  background: var(--border-subtle);
}

.segmented-progress span {
  height: 100%;
  transition: width 0.25s ease;
}

.segmented-progress .is-admit {
  background: var(--success);
}

.segmented-progress .is-review {
  background: var(--warning);
}

.segmented-progress .is-exclude {
  background: var(--danger);
}

.progress-legend {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-top: 8px;
  flex-wrap: wrap;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: var(--text-secondary);
  font-size: 11px;
}

.legend-item strong {
  color: var(--text-primary);
  font-family: var(--font-mono);
}

.legend-item em {
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-style: normal;
}

.legend-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--text-muted);
}

.legend-dot.is-admit {
  background: var(--success);
}

.legend-dot.is-review {
  background: var(--warning);
}

.legend-dot.is-exclude {
  background: var(--danger);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-top: 18px;
}

.summary-card {
  position: relative;
  min-width: 0;
  padding: 15px;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  background: var(--surface-card);
  box-shadow: 0 1px 2px 0 rgba(15, 23, 42, 0.03);
  color: var(--text-primary);
  line-height: 1.5;
}

.summary-card.selectable {
  width: 100%;
  font: inherit;
  text-align: left;
  cursor: pointer;
  transition: border-color 0.16s ease, box-shadow 0.16s ease, transform 0.16s ease;
}

.summary-card.selectable:hover {
  border-color: var(--border-strong);
  box-shadow: 0 4px 12px -4px rgba(15, 23, 42, 0.12);
  transform: translateY(-1px);
}

.summary-card.selectable:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
}

.summary-card.selected.review {
  border-color: rgba(245, 158, 11, 0.72);
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.14);
}

.summary-card.selected.exclude {
  border-color: rgba(244, 63, 94, 0.72);
  box-shadow: 0 0 0 3px rgba(244, 63, 94, 0.13);
}

.summary-card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.summary-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.summary-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--text-muted);
}

.summary-card.admit .summary-dot {
  background: var(--success);
}

.summary-card.review .summary-dot,
.candidate-title-group .summary-dot.is-review {
  background: var(--warning);
}

.summary-card.exclude .summary-dot,
.candidate-title-group .summary-dot.is-exclude {
  background: var(--danger);
}

.summary-card.total .summary-dot {
  background: var(--primary);
}

.summary-percent {
  padding: 2px 6px;
  border-radius: 999px;
  color: var(--text-secondary);
  background: var(--surface-subtle);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  white-space: nowrap;
}

.summary-card.admit .summary-percent {
  color: #047857;
  background: #ecfdf5;
}

.summary-card.review .summary-percent {
  color: #b45309;
  background: #fffbeb;
}

.summary-card.exclude .summary-percent {
  color: #be123c;
  background: #fff1f2;
}

.summary-value {
  display: block;
  margin-top: 9px;
  color: var(--text-primary);
  font-family: var(--font-display);
  font-size: 28px;
  font-weight: 700;
  line-height: 32px;
  letter-spacing: -0.02em;
}

.summary-card.admit .summary-value {
  color: #047857;
}

.summary-card.review .summary-value {
  color: #b45309;
}

.summary-card.exclude .summary-value {
  color: #be123c;
}

.summary-card.total .summary-value {
  color: var(--primary);
}

.summary-foot {
  display: block;
  margin-top: 8px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 16px;
}

.active-badge {
  position: absolute;
  top: -9px;
  right: 12px;
  z-index: 1;
  padding: 2px 7px;
  border-radius: 999px;
  color: #ffffff;
  background: var(--warning);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  box-shadow: 0 2px 5px rgba(245, 158, 11, 0.28);
}

.summary-card.selected.exclude .active-badge {
  background: var(--danger);
  box-shadow: 0 2px 5px rgba(244, 63, 94, 0.26);
}

.exclusion-note {
  margin-top: 16px;
  border-radius: 8px;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
}

.download-link {
  color: var(--primary);
  font-size: 13px;
  text-decoration: none;
  cursor: pointer;
}

.download-link:hover {
  text-decoration: underline;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-card);
}

.section-copy {
  min-width: 0;
}

.section-copy h2 {
  font-size: 18px;
  line-height: 24px;
}

.section-pill {
  flex: 0 0 auto;
  padding: 3px 8px;
  color: var(--primary);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  padding: 20px;
}

.metrics-grid :deep(.metric-card) {
  min-width: 0;
  border-color: var(--border-subtle);
  border-radius: 10px;
  box-shadow: 0 1px 2px 0 rgba(15, 23, 42, 0.03);
}

.metrics-grid :deep(.metric-card > .el-card__header) {
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--border-subtle);
  background: var(--surface-card);
}

.metrics-grid :deep(.metric-card > .el-card__body) {
  padding: 14px 16px 16px;
}

.candidate-header {
  align-items: center;
  flex-wrap: wrap;
}

.candidate-title-group {
  gap: 10px;
}

.candidate-count {
  padding: 3px 8px;
  color: var(--text-secondary);
  background: var(--surface-subtle);
  border-color: var(--border-subtle);
}

.candidate-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.candidate-actions :deep(.el-button) {
  border-radius: 8px;
}

.candidate-body {
  padding: 0 16px 16px;
}

.candidate-table {
  width: 100%;
}

.candidate-table :deep(.el-table__header th.el-table__cell) {
  height: 40px;
  padding: 0;
  border-bottom: 1px solid var(--border-strong);
  color: var(--text-secondary);
  background: var(--surface-subtle);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.candidate-table :deep(.el-table__body td.el-table__cell) {
  padding: 9px 0;
  border-bottom: 1px solid #eef2f7;
  color: var(--text-secondary);
}

.candidate-table :deep(.el-table__body tr:hover > td.el-table__cell) {
  background: #f8fafc;
}

.candidate-thumb {
  display: block;
  width: 58px;
  height: 58px;
  object-fit: cover;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  cursor: zoom-in;
}

.candidate-thumb.is-loading {
  opacity: 0.55;
  cursor: progress;
}

.thumb-placeholder {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 58px;
  height: 58px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  color: var(--text-muted);
  background: var(--surface-subtle);
  font-size: 10px;
}

.thumb-placeholder.is-broken {
  color: var(--danger);
  background: #fff1f2;
  border-color: #fecdd3;
}

.metric-cell {
  display: inline-block;
  min-width: 48px;
  padding: 2px 5px;
  border-radius: 4px;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  text-align: right;
}

.metric-cell.is-warning {
  color: #b45309;
  background: #fffbeb;
  font-weight: 600;
}

.metric-cell.is-danger {
  color: #be123c;
  background: #fff1f2;
  font-weight: 600;
}

.metric-cell.is-muted {
  color: var(--text-muted);
  background: transparent;
  font-weight: 400;
}

.recommendation-chip.is-admit {
  color: #047857;
  background: #ecfdf5;
}

.recommendation-chip.is-admit .status-dot {
  background: var(--success);
}

.recommendation-chip.is-review {
  color: #b45309;
  background: #fffbeb;
}

.recommendation-chip.is-review .status-dot {
  background: var(--warning);
}

.recommendation-chip.is-exclude {
  color: #be123c;
  background: #fff1f2;
}

.recommendation-chip.is-exclude .status-dot {
  background: var(--danger);
}

.reason-text {
  color: var(--text-secondary);
  line-height: 1.45;
}

@keyframes status-pulse {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.9);
  }

  50% {
    opacity: 1;
    transform: scale(1.2);
  }
}

@media (min-width: 1440px) {
  .metrics-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 1100px) {
  .hero-header {
    flex-direction: column;
  }

  .hero-toolbar {
    justify-content: flex-start;
    width: 100%;
  }

  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 900px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .quality-page {
    padding: 14px;
  }

  .hero-panel,
  .section-header {
    padding: 14px;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .profile-select {
    width: 100%;
  }

  .profile-control {
    width: 100%;
  }

  .job-strip-top,
  .candidate-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .job-progress {
    width: 100%;
  }

  .metrics-grid {
    padding: 14px;
  }
}
</style>
