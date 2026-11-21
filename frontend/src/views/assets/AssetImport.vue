<template>
  <div class="asset-import-page">
    <section class="page-hero">
      <div class="hero-copy">
        <div class="breadcrumb">
          <!-- <span>资产库</span>
          <el-icon><ArrowRight /></el-icon>
          <span class="breadcrumb-current">导入任务</span> -->
        </div>
        <div class="hero-title-row">
          <h1>图像资源导入</h1>
          <!-- <span class="tech-chip">IMPORT WORKBENCH</span> -->
        </div>
        <p class="hero-subtitle">
          本地存储路径扫描、花卉品类识别与标注匹配预检，确认后加入资产导入队列。
        </p>
      </div>

      <div class="workflow-stepper" aria-label="导入工作流">
        <template v-for="(step, index) in workflowSteps" :key="step.label">
          <div
            class="workflow-step"
            :class="{
              complete: index + 1 < activeStep,
              current: index + 1 === activeStep,
            }"
          >
            <div class="workflow-step-indicator">
              <el-icon v-if="index + 1 < activeStep"><CircleCheck /></el-icon>
              <span v-else>{{ index + 1 }}</span>
            </div>
            <span class="workflow-step-label">{{ step.label }}</span>
          </div>
          <div
            v-if="index < workflowSteps.length - 1"
            class="workflow-divider"
            :class="{ filled: index + 1 < activeStep }"
          ></div>
        </template>
      </div>
    </section>

    <section class="config-grid" aria-label="导入配置">
      <article class="config-card">
        <div class="card-header">
          <div class="card-title-group">
            <div class="card-icon">
              <el-icon><FolderOpened /></el-icon>
            </div>
            <div>
              <h2>存储路径与扫描范围</h2>
              <span class="card-subtitle">Storage & Directory Source</span>
            </div>
          </div>
          <span class="card-status">
            <span class="status-dot"></span>
            等待扫描
          </span>
        </div>

        <div class="card-body">
          <div class="field-group">
            <div class="field-label-row">
              <label class="field-label">
                图片存储绝对路径 <span class="required">*</span>
              </label>
              <span class="field-help">支持项目资产根目录下的本地绝对路径</span>
            </div>
            <el-input
              v-model="form.image_path"
              class="field-control"
              size="large"
              clearable
              placeholder="/data/datasets/flora_inbound/"
            >
              <template #prefix>
                <el-icon><FolderOpened /></el-icon>
              </template>
            </el-input>
          </div>

          <div class="toggle-card">
            <div class="toggle-copy">
              <div class="field-label">递归遍历子目录</div>
              <p>启用后深度扫描所有多层级嵌套目录。</p>
            </div>
            <el-switch
              v-model="form.recursive"
              size="large"
              active-text="递归"
              inactive-text="仅当前"
            />
          </div>

          <div class="field-group">
            <div class="field-label-row">
              <label class="field-label">批次备注标识</label>
              <span class="field-help">可选，用于导入记录中的批次追踪。</span>
            </div>
            <el-input
              v-model="form.batch_name"
              class="field-control"
              size="large"
              clearable
              placeholder="例如：2025 高山杜鹃实拍批次 A"
            >
              <template #prefix>
                <el-icon><EditPen /></el-icon>
              </template>
            </el-input>
          </div>
        </div>

        <div class="card-footer-note">
          <el-icon><InfoFilled /></el-icon>
          <span>支持 JPEG、PNG、TIFF、RAW 等图像文件。</span>
        </div>
      </article>

      <article class="config-card">
        <div class="card-header">
          <div class="card-title-group">
            <div class="card-icon">
              <el-icon><CollectionTag /></el-icon>
            </div>
            <div>
              <h2>分类学与多模态属性</h2>
              <span class="card-subtitle">Taxonomy & Spectral Config</span>
            </div>
          </div>
          <span class="card-status neutral">
            <span class="status-dot"></span>
            分类配置
          </span>
        </div>

        <div class="card-body">
          <div class="field-group">
            <div class="field-label-row">
              <label class="field-label">
                目标花卉分类 <span class="required">*</span>
              </label>
              <span class="field-help">选择资产入库归属类别。</span>
            </div>
            <el-select
              v-model="form.category"
              class="field-control category-select"
              size="large"
              filterable
              placeholder="请选择花卉类别"
            >
              <el-option
                v-for="category in categories"
                :key="category.id"
                :label="category.display_name"
                :value="category.name"
              >
                <div class="category-option">
                  <span>{{ category.display_name }}</span>
                  <span class="category-option-code">{{ category.name }}</span>
                </div>
              </el-option>
            </el-select>
          </div>

          <div class="segment-grid">
            <div class="segment-group">
              <label class="field-label">一级采集类型</label>
              <div class="segmented-control">
                <button
                  v-for="option in captureTypes"
                  :key="option.value"
                  type="button"
                  class="segment-option"
                  :class="{ active: form.capture_type === option.value }"
                  @click="setCaptureType(option.value)"
                >
                  <el-icon><component :is="option.icon" /></el-icon>
                  <span>{{ option.label }}</span>
                </button>
              </div>
            </div>

            <div class="segment-group">
              <label class="field-label">
                二级光谱模态
                <span v-if="!form.capture_type" class="field-hint">先选择一级类型</span>
              </label>
              <div
                class="segmented-control"
                :class="{ disabled: !form.capture_type }"
              >
                <button
                  v-for="option in spectralTypes"
                  :key="option.value"
                  type="button"
                  class="segment-option"
                  :class="{ active: form.spectral_type === option.value }"
                  :disabled="!form.capture_type"
                  @click="setSpectralType(option.value)"
                >
                  <el-icon><component :is="option.icon" /></el-icon>
                  <span>{{ option.label }}</span>
                </button>
              </div>
            </div>
          </div>

          <div class="field-group">
            <div class="field-label-row">
              <label class="field-label">关联标注文件或目录</label>
              <span class="field-help">可选，支持 XML / JSON 等标注文件。</span>
            </div>
            <el-input
              v-model="form.annotation_path"
              class="field-control"
              size="large"
              clearable
              placeholder="/data/annotations/flora_pascal_voc.xml"
            >
              <template #prefix>
                <el-icon><EditPen /></el-icon>
              </template>
            </el-input>
          </div>

          <div class="field-group">
            <div class="field-label-row">
              <label class="field-label">自定义入库标签</label>
              <span class="field-help">{{ form.tags.length }}/5</span>
            </div>
            <div class="tag-editor">
              <span
                v-for="(tag, index) in form.tags"
                :key="`${tag}-${index}`"
                class="tag-chip"
              >
                <span>{{ tag }}</span>
                <button type="button" aria-label="移除标签" @click.stop="removeTag(index)">
                  <el-icon><Close /></el-icon>
                </button>
              </span>
              <input
                v-model="tagDraft"
                class="tag-input"
                placeholder="+ 添加业务标签（回车确认）"
                @keydown.enter.prevent="addTag"
                @keydown="onTagKeydown"
                @blur="addTag"
              />
            </div>
          </div>
        </div>

        <div class="card-actions">
          <button type="button" class="text-action" @click="resetForm">
            <el-icon><Refresh /></el-icon>
            清空重置
          </button>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            @click="submitScan"
          >
            <el-icon><Search /></el-icon>
            扫描预览
          </el-button>
        </div>
      </article>
    </section>

    <section v-if="preview" class="preview-section">
      <div
        class="preview-banner"
        :class="hasWarnings ? 'warning' : 'success'"
      >
        <div class="banner-icon">
          <el-icon v-if="hasWarnings"><Warning /></el-icon>
          <el-icon v-else><CircleCheck /></el-icon>
        </div>
        <div class="banner-copy">
          <div class="banner-title-row">
            <h2>扫描预览已就绪</h2>
            <code>BATCH #{{ batchId }}</code>
          </div>
          <p>{{ bannerDescription }}</p>
        </div>
        <div class="banner-stats">
          <div>
            <span>影像总数</span>
            <strong>{{ imageCount.toLocaleString() }}</strong>
          </div>
          <div>
            <span>预检告警</span>
            <strong>{{ warningCount }}</strong>
          </div>
        </div>
      </div>

      <div class="metric-grid">
        <article
          v-for="metric in metrics"
          :key="metric.key"
          class="metric-card"
          :class="`tone-${metric.tone}`"
        >
          <div class="metric-top">
            <span>{{ metric.label }}</span>
            <el-icon><component :is="metric.icon" /></el-icon>
          </div>
          <div class="metric-value">
            {{ metric.value }}
            <span v-if="metric.unit" class="metric-unit">{{ metric.unit }}</span>
          </div>
          <div class="metric-meta">{{ metric.meta }}</div>
        </article>
      </div>

      <div class="consistency-card">
        <div class="consistency-head">
          <div>
            <h3>标注映射与一致性比例</h3>
            <span>{{ annotationMatched.toLocaleString() }} / {{ imageCount.toLocaleString() }} 精确匹配</span>
          </div>
          <div class="consistency-legend">
            <span
              v-for="segment in annotationSegments"
              :key="segment.key"
              class="legend-item"
            >
              <i :class="`legend-dot ${segment.tone}`"></i>
              {{ segment.label }}
              <strong>{{ segment.percent.toFixed(1) }}%</strong>
            </span>
          </div>
        </div>
        <div class="stacked-progress">
          <div
            v-for="segment in annotationSegments"
            :key="`bar-${segment.key}`"
            class="progress-segment"
            :class="segment.tone"
            :style="{ width: `${segment.percent}%` }"
          ></div>
        </div>
      </div>

      <div class="preview-actions">
        <el-button size="large" class="ghost-action" @click="scrollToConfig">
          重新调整参数
        </el-button>
        <el-button
          size="large"
          class="quality-action"
          :disabled="!batchId"
          @click="openQuality"
        >
          <el-icon><DataLine /></el-icon>
          进入质量体检
        </el-button>
        <el-button
          type="success"
          size="large"
          class="confirm-action"
          :loading="confirming"
          @click="confirm"
        >
          <el-icon><Upload /></el-icon>
          确认并加入导入队列
        </el-button>
      </div>
    </section>
  </div>
</template>

<script setup>
import {
  ArrowRight,
  Camera,
  CircleCheck,
  Close,
  CollectionTag,
  DataLine,
  EditPen,
  Filter,
  FolderOpened,
  InfoFilled,
  Picture,
  Refresh,
  Search,
  Sunny,
  Upload,
  Warning,
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  confirmAssetImport,
  getAssetCategories,
  scanAssetImport,
} from '@/services/assetImportService'

const router = useRouter()

const categories = ref([])
const loading = ref(false)
const confirming = ref(false)
const preview = ref(null)
const batchId = ref(null)
const tagDraft = ref('')

const form = reactive({
  image_path: '',
  category: '',
  annotation_path: '',
  capture_type: '',
  spectral_type: '',
  tags: [],
  recursive: true,
  batch_name: '',
})

const captureTypes = [
  { label: '实拍', value: 'photo', icon: Camera },
  { label: '手绘标本', value: 'hand_drawn', icon: EditPen },
]

const spectralTypes = [
  { label: '可见光 (RGB)', value: 'visible', icon: Sunny },
  { label: '红外 (NIR)', value: 'infrared', icon: Filter },
]

const workflowSteps = [
  { label: '扫描配置', icon: Search },
  { label: '预检与标注匹配', icon: CircleCheck },
  { label: '质量体检', icon: DataLine },
  { label: '加入导入队列', icon: Upload },
]

const activeStep = computed(() => (preview.value ? 2 : 1))

const annotationMatching = computed(
  () => preview.value?.annotation_matching || { matched: 0, ambiguous: 0, unmatched: 0 },
)
const imageCount = computed(() => Number(preview.value?.image_count || 0))
const issueCount = computed(() => Number(preview.value?.issue_count || 0))
const annotationMatched = computed(() => Number(annotationMatching.value.matched || 0))
const annotationAmbiguous = computed(() => Number(annotationMatching.value.ambiguous || 0))
const annotationUnmatched = computed(() => Number(annotationMatching.value.unmatched || 0))

const matchedRate = computed(() => {
  if (!imageCount.value) return 0
  return (annotationMatched.value / imageCount.value) * 100
})

const ambiguousRate = computed(() => {
  if (!imageCount.value) return 0
  return (annotationAmbiguous.value / imageCount.value) * 100
})

const unmatchedRate = computed(() => {
  if (!imageCount.value) return 0
  return (annotationUnmatched.value / imageCount.value) * 100
})

const warningCount = computed(
  () => issueCount.value + annotationAmbiguous.value + annotationUnmatched.value,
)
const hasWarnings = computed(() => warningCount.value > 0)

const metrics = computed(() => [
  {
    key: 'total',
    label: '待入库影像总数',
    value: imageCount.value.toLocaleString(),
    unit: '张',
    meta: '扫描预览完成，等待确认入库',
    icon: Picture,
    tone: 'primary',
  },
  {
    key: 'match',
    label: '标注匹配精确率',
    value: `${matchedRate.value.toFixed(1)}%`,
    unit: '',
    meta: `${annotationMatched.value.toLocaleString()} 张精确匹配`,
    icon: CircleCheck,
    tone: 'success',
  },
  {
    key: 'warning',
    label: '预检异常与告警',
    value: warningCount.value.toLocaleString(),
    unit: '项',
    meta: `${annotationAmbiguous.value} 歧义 / ${annotationUnmatched.value} 未匹配`,
    icon: Warning,
    tone: warningCount.value > 0 ? 'warning' : 'success',
  },
  {
    key: 'coverage',
    label: '标注覆盖分布',
    value: `${annotationMatched.value.toLocaleString()} / ${imageCount.value.toLocaleString()}`,
    unit: '',
    meta: '已匹配 / 待入库影像总数',
    icon: DataLine,
    tone: 'info',
  },
])

const annotationSegments = computed(() => [
  {
    key: 'matched',
    label: '精确对齐',
    percent: matchedRate.value,
    tone: 'success',
  },
  {
    key: 'ambiguous',
    label: '命名轻微歧义',
    percent: ambiguousRate.value,
    tone: 'warning',
  },
  {
    key: 'unmatched',
    label: '缺漏标注',
    percent: unmatchedRate.value,
    tone: 'muted',
  },
])

const bannerDescription = computed(() => {
  const total = imageCount.value.toLocaleString()
  const matched = annotationMatched.value.toLocaleString()
  const ambiguous = annotationAmbiguous.value
  const unmatched = annotationUnmatched.value

  if (!form.annotation_path) {
    return `已识别 ${total} 个影像切片，当前未配置标注路径。`
  }

  return `已识别 ${total} 个影像切片，其中 ${matched} 张精确匹配，${ambiguous} 张存在歧义，${unmatched} 张未匹配标注。`
})

const setCaptureType = (value) => {
  if (form.capture_type === value) {
    form.capture_type = ''
    form.spectral_type = ''
    return
  }

  form.capture_type = value
}

const setSpectralType = (value) => {
  if (!form.capture_type) return
  form.spectral_type = form.spectral_type === value ? '' : value
}

const addTag = () => {
  const value = tagDraft.value.trim()
  tagDraft.value = ''

  if (!value) return
  if (form.tags.includes(value)) {
    ElMessage.info('该标签已存在')
    return
  }
  if (form.tags.length >= 5) {
    ElMessage.warning('最多添加 5 个标签')
    return
  }

  form.tags.push(value)
}

const removeTag = (index) => {
  form.tags.splice(index, 1)
}

const onTagKeydown = (event) => {
  if (event.key === 'Backspace' && !tagDraft.value && form.tags.length) {
    form.tags.pop()
  }
}

const submitScan = async () => {
  if (!form.image_path.trim() || !form.category) {
    ElMessage.warning('请先填写图片路径和花卉类别')
    return
  }

  loading.value = true
  preview.value = null
  batchId.value = null

  try {
    const payload = {
      ...form,
      image_path: form.image_path.trim(),
      annotation_path: form.annotation_path.trim() || null,
      batch_name: form.batch_name.trim() || null,
      capture_type: form.capture_type || null,
      spectral_type: form.spectral_type || null,
    }
    const result = await scanAssetImport(payload)
    batchId.value = result.batch_id
    preview.value = result
    ElMessage.success('扫描完成')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '扫描失败')
  } finally {
    loading.value = false
  }
}

const confirm = async () => {
  if (!batchId.value) return

  confirming.value = true
  try {
    const result = await confirmAssetImport(batchId.value)
    ElMessage.success(result.message || '已加入导入队列')
    preview.value = null
    batchId.value = null
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '确认失败')
  } finally {
    confirming.value = false
  }
}

const openQuality = () => {
  if (!batchId.value) return
  router.push(`/assets/quality/${batchId.value}`)
}

const resetForm = () => {
  form.image_path = ''
  form.category = ''
  form.annotation_path = ''
  form.capture_type = ''
  form.spectral_type = ''
  form.tags = []
  form.recursive = true
  form.batch_name = ''
  tagDraft.value = ''
  preview.value = null
  batchId.value = null
}

const scrollToConfig = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

onMounted(async () => {
  try {
    categories.value = await getAssetCategories()
  } catch (error) {
    ElMessage.error('加载资产类别失败')
  }
})
</script>

<style scoped>
.asset-import-page {
  --canvas: #f8fafc;
  --surface: #ffffff;
  --surface-subtle: #f1f5f9;
  --surface-blue: #eff6ff;
  --border-subtle: #e2e8f0;
  --border-strong: #cbd5e1;
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  --success: #10b981;
  --success-bg: #ecfdf5;
  --success-text: #047857;
  --warning: #f59e0b;
  --warning-bg: #fffbeb;
  --warning-text: #b45309;
  --danger: #f43f5e;
  --danger-bg: #fff1f2;
  --danger-text: #be123c;

  box-sizing: border-box;
  width: 100%;
  min-width: 0;
  margin: 0;
  padding: 20px;
  color: var(--text-primary);
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--canvas);
}

.page-hero {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  padding: 24px;
  background: var(--surface);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-muted);
  font-size: 12px;
}

.breadcrumb-current {
  color: var(--primary);
  font-weight: 600;
}

.hero-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.hero-title-row h1 {
  margin: 0;
  font-size: 26px;
  line-height: 32px;
  letter-spacing: -0.01em;
}

.tech-chip {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  color: var(--primary);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  background: var(--surface-blue);
  border-radius: 6px;
}

.hero-subtitle {
  max-width: 660px;
  margin: 10px 0 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.workflow-stepper {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  padding: 8px;
  background: var(--surface-subtle);
  border-radius: 12px;
}

.workflow-step {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 10px;
  color: var(--text-muted);
  border-radius: 8px;
  white-space: nowrap;
}

.workflow-step.current {
  color: #ffffff;
  background: var(--primary);
  box-shadow: 0 1px 2px rgba(37, 99, 235, 0.22);
}

.workflow-step.complete {
  color: var(--primary);
  background: #ffffff;
}

.workflow-step-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
  background: #ffffff;
}

.workflow-step.current .workflow-step-indicator {
  color: var(--primary);
}

.workflow-step.complete .workflow-step-indicator {
  color: #ffffff;
  background: var(--primary);
}

.workflow-step-label {
  font-size: 12px;
  font-weight: 600;
}

.workflow-divider {
  width: 22px;
  height: 2px;
  background: var(--border-strong);
  border-radius: 999px;
}

.workflow-divider.filled {
  background: var(--primary);
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  gap: 16px;
  margin-top: 16px;
}

.config-card {
  grid-column: span 6;
  display: flex;
  flex-direction: column;
  min-width: 0;
  padding: 20px;
  background: var(--surface);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding-bottom: 14px;
  border-bottom: 1px solid var(--border-subtle);
}

.card-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
}

.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  color: var(--primary);
  font-size: 20px;
  background: var(--surface-blue);
  border-radius: 8px;
}

.card-title-group h2 {
  margin: 0;
  font-size: 15px;
  line-height: 20px;
}

.card-subtitle {
  color: var(--text-muted);
  font-size: 11px;
  line-height: 15px;
}

.card-status {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 8px;
  color: var(--primary);
  font-size: 11px;
  font-weight: 600;
  background: var(--surface-blue);
  border-radius: 6px;
  white-space: nowrap;
}

.card-status.neutral {
  color: var(--text-secondary);
  background: var(--surface-subtle);
}

.status-dot {
  width: 6px;
  height: 6px;
  background: var(--primary);
  border-radius: 50%;
}

.card-status.neutral .status-dot {
  background: var(--text-muted);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-top: 18px;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.field-label-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.field-label {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 600;
}

.required {
  color: var(--danger);
}

.field-help {
  color: var(--text-muted);
  font-size: 11px;
}

.field-hint {
  color: var(--warning-text);
  font-weight: 400;
}

.field-control {
  width: 100%;
}

.asset-import-page :deep(.el-input__wrapper),
.asset-import-page :deep(.el-select__wrapper) {
  min-height: 40px;
  background: var(--surface-subtle);
  border: 1px solid transparent;
  box-shadow: none;
}

.asset-import-page :deep(.el-input__wrapper:hover),
.asset-import-page :deep(.el-select__wrapper:hover) {
  border-color: var(--border-strong);
}

.asset-import-page :deep(.el-input__wrapper.is-focus),
.asset-import-page :deep(.el-select__wrapper.is-focused) {
  background: #ffffff;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}

.asset-import-page :deep(.el-input__inner),
.asset-import-page :deep(.el-select__selected-item) {
  color: var(--text-primary);
}

.toggle-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px;
  background: var(--surface-subtle);
  border-radius: 10px;
}

.toggle-copy p {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.45;
}

.card-footer-note {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 18px;
  color: var(--text-muted);
  font-size: 11px;
}

.category-select {
  width: 100%;
}

.category-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
}

.category-option-code {
  color: var(--text-muted);
  font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
}

.segment-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.segment-group {
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.segmented-control {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 1fr;
  gap: 3px;
  padding: 4px;
  background: var(--surface-subtle);
  border-radius: 10px;
}

.segmented-control.disabled {
  opacity: 0.58;
}

.segment-option {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-width: 0;
  padding: 9px 8px;
  color: var(--text-secondary);
  font: inherit;
  font-size: 12px;
  white-space: nowrap;
  background: transparent;
  border: 0;
  border-radius: 7px;
  cursor: pointer;
  transition: color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease;
}

.segment-option:hover:not(:disabled) {
  color: var(--text-primary);
}

.segment-option.active {
  color: var(--primary);
  background: #ffffff;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08);
}

.segment-option:disabled {
  cursor: not-allowed;
}

.tag-editor {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 7px;
  min-height: 44px;
  padding: 7px;
  background: var(--surface-subtle);
  border: 1px solid transparent;
  border-radius: 10px;
  cursor: text;
  transition: border-color 0.2s ease, background-color 0.2s ease, box-shadow 0.2s ease;
}

.tag-editor:focus-within {
  background: #ffffff;
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.1);
}

.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 7px;
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 500;
  background: #ffffff;
  border: 1px solid var(--border-subtle);
  border-radius: 7px;
  box-shadow: 0 1px 1px rgba(15, 23, 42, 0.04);
}

.tag-chip button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  padding: 0;
  color: var(--text-muted);
  background: transparent;
  border: 0;
  border-radius: 4px;
  cursor: pointer;
}

.tag-chip button:hover {
  color: var(--danger-text);
  background: var(--danger-bg);
}

.tag-input {
  flex: 1;
  min-width: 180px;
  padding: 4px 2px;
  color: var(--text-primary);
  font: inherit;
  font-size: 13px;
  background: transparent;
  border: 0;
  outline: 0;
}

.tag-input::placeholder {
  color: var(--text-muted);
}

.card-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--border-subtle);
}

.text-action {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  margin-right: auto;
  padding: 8px 10px;
  color: var(--text-secondary);
  font: inherit;
  font-size: 12px;
  background: transparent;
  border: 0;
  border-radius: 8px;
  cursor: pointer;
  transition: color 0.2s ease, background-color 0.2s ease;
}

.text-action:hover {
  color: var(--danger-text);
  background: var(--danger-bg);
}

.preview-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin-top: 16px;
}

.preview-banner {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  border-radius: 12px;
  border: 1px solid var(--border-subtle);
}

.preview-banner.success {
  background: var(--success-bg);
  border-left: 4px solid var(--success);
}

.preview-banner.warning {
  background: var(--warning-bg);
  border-left: 4px solid var(--warning);
}

.banner-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  font-size: 24px;
  background: rgba(255, 255, 255, 0.72);
  border-radius: 10px;
}

.preview-banner.success .banner-icon {
  color: var(--success-text);
}

.preview-banner.warning .banner-icon {
  color: var(--warning-text);
}

.banner-copy {
  flex: 1;
  min-width: 0;
}

.banner-title-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.banner-title-row h2 {
  margin: 0;
  font-size: 15px;
  line-height: 20px;
}

.banner-title-row code {
  padding: 2px 6px;
  color: var(--text-secondary);
  font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  background: rgba(255, 255, 255, 0.72);
  border-radius: 5px;
}

.banner-copy p {
  margin: 5px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.5;
}

.banner-stats {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-shrink: 0;
}

.banner-stats > div {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.banner-stats span {
  color: var(--text-muted);
  font-size: 11px;
}

.banner-stats strong {
  color: var(--text-primary);
  font-size: 16px;
  line-height: 20px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
}

.metric-card {
  min-width: 0;
  padding: 16px;
  background: var(--surface-subtle);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
}

.metric-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.metric-top .el-icon {
  font-size: 20px;
}

.tone-primary .metric-top .el-icon {
  color: var(--primary);
}

.tone-success .metric-top .el-icon {
  color: var(--success);
}

.tone-warning .metric-top .el-icon {
  color: var(--warning);
}

.tone-info .metric-top .el-icon {
  color: var(--primary);
}

.metric-value {
  margin-top: 10px;
  color: var(--text-primary);
  font-size: 30px;
  font-weight: 700;
  line-height: 34px;
  letter-spacing: -0.02em;
}

.tone-success .metric-value {
  color: var(--success-text);
}

.tone-warning .metric-value {
  color: var(--warning-text);
}

.metric-unit {
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0;
}

.metric-meta {
  margin-top: 7px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.4;
}

.consistency-card {
  padding: 16px;
  background: var(--surface);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
}

.consistency-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.consistency-head h3 {
  margin: 0;
  font-size: 14px;
  line-height: 20px;
}

.consistency-head > div:first-child span {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 11px;
}

.consistency-legend {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 14px;
  color: var(--text-secondary);
  font-size: 11px;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}

.legend-item strong {
  color: var(--text-primary);
  font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  font-weight: 500;
}

.legend-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
}

.legend-dot.success {
  background: var(--success);
}

.legend-dot.warning {
  background: var(--warning);
}

.legend-dot.muted {
  background: var(--text-muted);
}

.stacked-progress {
  display: flex;
  height: 12px;
  margin-top: 14px;
  overflow: hidden;
  background: var(--border-subtle);
  border-radius: 6px;
}

.progress-segment {
  height: 100%;
}

.progress-segment.success {
  background: var(--success);
}

.progress-segment.warning {
  background: var(--warning);
}

.progress-segment.muted {
  background: var(--text-muted);
}

.preview-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.08);
}

.ghost-action {
  color: var(--text-secondary);
  background: transparent;
  border-color: var(--border-strong);
}

.ghost-action:hover {
  color: var(--text-primary);
  background: var(--surface-subtle);
  border-color: var(--border-strong);
}

.quality-action {
  color: var(--primary);
  background: var(--surface-blue);
  border-color: var(--surface-blue);
}

.quality-action:hover {
  color: #ffffff;
  background: var(--primary);
  border-color: var(--primary);
}

.confirm-action {
  border-color: var(--success);
}

@media (max-width: 1180px) {
  .page-hero {
    flex-direction: column;
  }

  .workflow-stepper {
    width: 100%;
    overflow-x: auto;
  }

  .config-card {
    grid-column: span 12;
  }

  .metric-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .asset-import-page {
    padding: 14px;
  }

  .segment-grid,
  .metric-grid {
    grid-template-columns: 1fr;
  }

  .preview-banner {
    align-items: flex-start;
    flex-direction: column;
  }

  .banner-stats {
    width: 100%;
    justify-content: flex-start;
  }

  .banner-stats > div {
    align-items: flex-start;
  }

  .consistency-head {
    flex-direction: column;
  }

  .preview-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .preview-actions .el-button {
    width: 100%;
    margin-left: 0;
  }
}
</style>
