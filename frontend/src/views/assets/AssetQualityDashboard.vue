<template>
  <el-container class="quality-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <div>
            <h2>入库前质量体检</h2>
            <p>批次 {{ batchId }} · 仅分析候选文件夹，不触发正式入库</p>
            <p v-if="!selectedProfileKey">全部画像：未调整的指标按图片画像评估；滑块调整会覆盖整个批次的对应阈值。</p>
          </div>
          <div class="actions">
            <el-select
              v-model="selectedProfileKey"
              clearable
              placeholder="全部画像"
              style="width: 220px"
              @change="onProfileChange"
            >
              <el-option
                v-for="profile in profiles"
                :key="profile.profile_key"
                :label="profile.profile_key"
                :value="profile.profile_key"
              />
            </el-select>
            <el-button :loading="creatingJob" @click="startJob">开始体检</el-button>
            <el-button :loading="loading" @click="loadAll">刷新</el-button>
          </div>
        </div>
      </template>

      <div v-if="job" class="job-strip">
        <el-tag :type="jobTagType">{{ job.state }}</el-tag>
        <span>
          {{ (job.candidate_progress?.completed || 0) + (job.candidate_progress?.failed || 0) }} /
          {{ job.candidate_progress?.total || job.total_count || 0 }}
        </span>
        <el-progress
          :percentage="jobPercent"
          :stroke-width="12"
          class="job-progress"
        />
      </div>

      <div v-if="preview" class="summary-grid">
        <div class="summary-card admit">
          <span>建议入库</span>
          <strong>{{ preview.counts.admit }}</strong>
        </div>
        <button
          type="button"
          class="summary-card review selectable"
          :class="{ selected: selectedRecommendation === 'review' }"
          :aria-pressed="selectedRecommendation === 'review'"
          @click="showCandidates('review')"
        >
          <span>建议复核</span>
          <strong>{{ preview.counts.review }}</strong>
          <small>点击查看图片</small>
        </button>
        <button
          type="button"
          class="summary-card exclude selectable"
          :class="{ selected: selectedRecommendation === 'exclude' }"
          :aria-pressed="selectedRecommendation === 'exclude'"
          @click="showCandidates('exclude')"
        >
          <span>建议排除</span>
          <strong>{{ preview.counts.exclude }}</strong>
          <small>点击查看图片</small>
        </button>
        <div class="summary-card total">
          <span>已评估</span>
          <strong>{{ preview.evaluated_count }}</strong>
        </div>
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
        <el-button type="primary" :disabled="!preview || previewLoading || !preview.evaluated_count" @click="freezeEvaluation">
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
    </el-card>

    <el-card v-loading="loading" class="metrics-card">
      <template #header>
        <span>指标分布</span>
      </template>
      <div class="metrics-grid">
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
    </el-card>

    <el-card v-if="selectedRecommendation" class="candidates-card">
      <template #header>
        <div class="panel-header">
          <span>{{ selectedRecommendation === 'review' ? '建议复核的图片' : '建议排除的图片' }}</span>
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
        </div>
      </template>
      <el-empty v-if="!previewLoading && !candidateTotal" description="暂无该类图片" />
      <el-table v-else v-loading="previewLoading" :data="candidates">
        <el-table-column label="预览" width="90">
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
            <span v-else-if="row.decode_status === 'ok'">
              {{ failedThumbnailIds[row.candidate_id] ? '预览失败' : '加载中' }}
            </span>
            <span v-else>损坏</span>
          </template>
        </el-table-column>
        <el-table-column prop="source_filename" label="文件名" min-width="150" />
        <el-table-column prop="category" label="类别" width="90" />
        <el-table-column label="类型" width="130">
          <template #default="{ row }">
            {{ row.capture_type || '未指定' }} / {{ row.spectral_type || '未指定' }}
          </template>
        </el-table-column>
        <el-table-column label="位深" prop="bit_depth" width="70" />
        <el-table-column label="模糊度" width="90">
          <template #default="{ row }">{{ formatMetric(row.metrics.blur_effect) }}</template>
        </el-table-column>
        <el-table-column label="对比度" width="90">
          <template #default="{ row }">{{ formatMetric(row.metrics.rms_contrast) }}</template>
        </el-table-column>
        <el-table-column label="噪声" width="90">
          <template #default="{ row }">{{ formatMetric(row.metrics.noise_sigma) }}</template>
        </el-table-column>
        <el-table-column label="过曝比例" width="100">
          <template #default="{ row }">{{ formatMetric(row.metrics.bright_fraction) }}</template>
        </el-table-column>
        <el-table-column label="建议" width="90">
          <template #default="{ row }">
            <el-tag :type="recommendationType(row.recommendation)">
              {{ recommendationText(row.recommendation) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="原因" min-width="180">
          <template #default="{ row }">{{ reasonText(row) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <ElImageViewer
      v-if="previewImageUrl"
      :url-list="[previewImageUrl]"
      @close="closeImagePreview"
    />

  </el-container>
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

const exclusionExplanation = computed(() => {
  const exact = preview.value?.flag_counts?.EXACT_DUPLICATE || 0
  const decode = preview.value?.flag_counts?.DECODE_FAILED || 0
  if (!exact && !decode) return ''
  return `关闭四项质量指标不会关闭独立的入库检查：完全重复 ${exact} 张，解码失败 ${decode} 张；这些图片仍建议排除。`
})

const jobPercent = computed(() => {
  const total = job.value?.candidate_progress?.total || job.value?.total_count || 0
  if (!total) return 0
  const processed = (job.value?.candidate_progress?.completed || 0)
    + (job.value?.candidate_progress?.failed || 0)
  return Math.min(100, Math.round((processed / total) * 100))
})

const jobTagType = computed(() => {
  if (job.value?.state === 'completed') return 'success'
  if (job.value?.state === 'failed') return 'danger'
  if (job.value?.state === 'processing') return 'primary'
  return 'info'
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
    ElMessage.success(`已创建体检任务 ${result.job_id}`)
    await loadJob(result.job_id)
    syncJobPolling()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创建体检任务失败')
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

function recommendationType(recommendation) {
  if (recommendation === 'admit') return 'success'
  if (recommendation === 'review') return 'warning'
  return 'danger'
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
  display: block;
  padding: 18px;
}

.page-header,
.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.page-header h2,
.page-header p,
.panel-header span {
  margin: 0;
}

.page-header p {
  margin-top: 5px;
  color: #64748b;
  font-size: 12px;
}

.actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.job-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  color: #334155;
  font-size: 13px;
}

.job-progress {
  width: 300px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.exclusion-note {
  margin-bottom: 14px;
}

.summary-card {
  padding: 14px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.summary-card.selectable {
  width: 100%;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.summary-card.selectable:hover,
.summary-card.selectable.selected {
  border-color: #94a3b8;
  box-shadow: 0 0 0 2px #e2e8f0;
}

.summary-card.selectable:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

.summary-card small {
  display: block;
  margin-top: 5px;
  color: #64748b;
  font-size: 11px;
}

.summary-card span {
  display: block;
  color: #64748b;
  font-size: 12px;
}

.summary-card strong {
  display: block;
  margin-top: 7px;
  font-family: "JetBrains Mono", "SFMono-Regular", Consolas, monospace;
  font-size: 24px;
}

.summary-card.admit strong {
  color: #16a34a;
}

.summary-card.review strong {
  color: #d97706;
}

.summary-card.exclude strong {
  color: #dc2626;
}

.summary-card.total strong {
  color: #2563eb;
}

.action-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.download-link {
  color: #2563eb;
  font-size: 13px;
  text-decoration: none;
  cursor: pointer;
}

.metrics-card,
.candidates-card {
  margin-bottom: 16px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.candidate-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.candidate-thumb {
  width: 58px;
  height: 58px;
  object-fit: cover;
  border-radius: 5px;
  cursor: zoom-in;
}

.candidate-thumb.is-loading {
  opacity: 0.55;
  cursor: progress;
}

@media (max-width: 1000px) {
  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .page-header,
  .panel-header {
    flex-direction: column;
  }
}

@media (max-width: 700px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
