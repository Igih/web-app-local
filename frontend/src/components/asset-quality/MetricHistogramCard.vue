<template>
  <el-card class="metric-card">
    <template #header>
      <div class="metric-header">
        <div class="metric-title">
          <div class="metric-name-row">
            <strong>{{ metric.display_name }}</strong>
            <el-tooltip placement="top" effect="dark" :show-after="150">
              <template #content>
                <div class="metric-help">
                  <div class="metric-help-row"><span>作用：</span>{{ helpDescription }}</div>
                  <div
                    v-for="line in thresholdHelp"
                    :key="line"
                    class="metric-help-row"
                  >
                    {{ line }}
                  </div>
                  <div class="metric-help-row">{{ directionHelp }}</div>
                </div>
              </template>
              <el-icon class="help-icon"><QuestionFilled /></el-icon>
            </el-tooltip>
          </div>
          <span class="metric-id">{{ metric.metric_id }}</span>
        </div>
        <el-switch v-model="enabled" @change="emitChange" />
      </div>
    </template>

    <div class="chart-wrap">
      <canvas :ref="setCanvasRef" />
    </div>
    <div class="meta-line">
      有效值 {{ histogram.value_count }} · 缺失 {{ histogram.missing_count }}
      · {{ metric.unit }}
    </div>

      <div class="slider-row">
        <span>复核阈值</span>
        <el-slider
          v-model="localReview"
          :min="minBound"
          :max="maxBound"
          :step="step"
          :disabled="!enabled"
          @input="onReviewInput"
        />
        <span class="slider-value">{{ localReview }}</span>
      </div>
      <div class="slider-row">
        <span>严重阈值</span>
        <el-slider
          v-model="localSevere"
          :min="minBound"
          :max="maxBound"
          :step="step"
          :disabled="!enabled"
          @input="onSevereInput"
        />
        <span class="slider-value">{{ localSevere }}</span>
      </div>
      <div class="slider-row">
        <span>达到严重阈值时建议排除</span>
        <el-switch v-model="severeEnabled" :disabled="!enabled" @change="emitChange" />
      </div>
  </el-card>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { QuestionFilled } from '@element-plus/icons-vue'
import Chart from 'chart.js/auto'

const props = defineProps({
  metric: { type: Object, required: true },
  histogram: { type: Object, required: true },
  thresholds: { type: Object, required: true },
  minBound: { type: Number, default: 0 },
  maxBound: { type: Number, default: 1 },
  step: { type: Number, default: 0.01 },
})

const emit = defineEmits(['threshold-change'])

const canvasEl = ref(null)
const chart = ref(null)
const enabled = ref(props.thresholds.enabled ?? true)
const severeEnabled = ref(props.thresholds.severe_enabled ?? false)

const localReview = ref(props.thresholds.review ?? 0)
const localSevere = ref(props.thresholds.severe ?? 1)

const METRIC_HELP = {
  blur_effect: '衡量图像模糊程度，数值越高通常表示越模糊。',
  rms_contrast: '衡量图像整体对比度，数值越高表示明暗差异越明显。',
  bright_fraction: '衡量亮度高于 0.95 的像素占比，用于提示可能的过曝；高亮内容也可能正常。',
  noise_sigma: '衡量图像噪声水平，数值越高通常表示噪声越明显。',
}

const helpDescription = computed(
  () => METRIC_HELP[props.metric.metric_id] || '暂无说明',
)

const thresholdHelp = computed(() => {
  return [
    `复核阈值：${formatHelpValue(localReview.value)}`,
    `严重阈值：${formatHelpValue(localSevere.value)}`,
    severeEnabled.value ? '达到严重阈值时建议排除。' : '严重自动排除已关闭，达到阈值仍建议复核。',
  ]
})

const directionHelp = computed(() => {
  if (props.metric.direction === 'high') {
    return '该指标按高风险处理：数值越大越接近复核或排除，数值越小越安全。'
  }
  return '该指标按低风险处理：数值越小越接近复核或排除，数值越大越安全。'
})

function formatHelpValue(value) {
  const numericValue = Number(value)
  if (!Number.isFinite(numericValue)) return '—'
  return numericValue.toFixed(2).replace(/\.?0+$/, '')
}

const setCanvasRef = (element) => {
  canvasEl.value = element
}

const thresholdLinePlugin = {
  id: 'thresholdLines',
  beforeDatasetsDraw(chartInstance) {
    const { ctx, chartArea, scales } = chartInstance
    if (!chartArea) return
    ctx.save()
    ctx.strokeStyle = 'rgba(220, 38, 38, 0.8)'
    ctx.lineWidth = 1.5
    for (const value of visibleThresholds.value) {
      const x = scales.x.getPixelForValue(value)
      if (x >= chartArea.left && x <= chartArea.right) {
        ctx.beginPath()
        ctx.moveTo(x, chartArea.top)
        ctx.lineTo(x, chartArea.bottom)
        ctx.stroke()
      }
    }
    ctx.restore()
  },
}

const visibleThresholds = computed(() => {
  if (!enabled.value) return []
  return [localReview.value, localSevere.value].filter(Number.isFinite)
})

function renderChart() {
  if (!canvasEl.value) return
  if (chart.value) {
    chart.value.destroy()
  }
  const edges = props.histogram.edges || []
  const points = props.histogram.counts.map((count, index) => ({
    x: (edges[index] + edges[index + 1]) / 2,
    y: count,
  }))
  chart.value = new Chart(canvasEl.value, {
    type: 'bar',
    data: {
      datasets: [
        {
          data: points,
          parsing: false,
          backgroundColor: 'rgba(37, 99, 235, 0.62)',
          borderWidth: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            title: (items) => {
              const index = items[0]?.dataIndex
              return index === undefined ? '' : `${edges[index].toFixed(2)} – ${edges[index + 1].toFixed(2)}`
            },
          },
        },
      },
      scales: {
        x: {
          type: 'linear',
          min: Math.min(props.minBound, edges[0] ?? props.minBound),
          max: Math.max(props.maxBound, edges[edges.length - 1] ?? props.maxBound),
          ticks: { maxTicksLimit: 8, font: { size: 10 } },
          grid: { display: false },
        },
        y: {
          beginAtZero: true,
          ticks: { precision: 0 },
        },
      },
    },
    plugins: [thresholdLinePlugin],
  })
}

function emitChange() {
  emitThresholds()
}

function onReviewInput(value) {
  const numericValue = Number(value)
  localReview.value = props.metric.direction === 'high'
    ? Math.min(numericValue, localSevere.value)
    : Math.max(numericValue, localSevere.value)
  emitThresholds()
}

function onSevereInput(value) {
  const numericValue = Number(value)
  localSevere.value = props.metric.direction === 'high'
    ? Math.max(numericValue, localReview.value)
    : Math.min(numericValue, localReview.value)
  emitThresholds()
}

function emitThresholds() {
  emit('threshold-change', {
    metric_id: props.metric.metric_id,
    enabled: enabled.value,
    severe_enabled: severeEnabled.value,
    direction: props.metric.direction,
    review: localReview.value,
    severe: localSevere.value,
  })
}

watch(() => props.histogram, renderChart, { deep: true })
watch(visibleThresholds, () => chart.value?.draw())

watch(() => props.thresholds, (thresholds) => {
  enabled.value = thresholds.enabled ?? true
  severeEnabled.value = thresholds.severe_enabled ?? false
  localReview.value = thresholds.review ?? 0
  localSevere.value = thresholds.severe ?? 1
}, { deep: true })

onMounted(renderChart)
onBeforeUnmount(() => {
  if (chart.value) chart.value.destroy()
})
</script>

<style scoped>
.metric-card {
  min-width: 0;
}

.metric-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.metric-title {
  min-width: 0;
}

.metric-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.help-icon {
  color: #94a3b8;
  cursor: help;
  font-size: 14px;
  flex: 0 0 auto;
}

.help-icon:hover {
  color: #2563eb;
}

.metric-id {
  display: block;
  margin-top: 4px;
  color: #94a3b8;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 11px;
}

.metric-help {
  max-width: 320px;
  line-height: 1.55;
}

.metric-help-row {
  margin: 3px 0;
}

.metric-help-row span {
  color: #93c5fd;
}

.chart-wrap {
  position: relative;
  height: 180px;
}

.meta-line {
  margin-top: 6px;
  color: #64748b;
  font-size: 12px;
}

.slider-row {
  display: grid;
  grid-template-columns: 90px 1fr 48px;
  gap: 10px;
  align-items: center;
  margin-top: 10px;
  color: #334155;
  font-size: 12px;
}

.slider-value {
  color: #2563eb;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", "Courier New", monospace;
  text-align: right;
}
</style>
