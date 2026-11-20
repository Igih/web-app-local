<template>
  <el-container class="import-records-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <span>导入任务</span>
          <el-button type="primary" @click="loadBatches()">刷新</el-button>
        </div>
      </template>
      <el-table v-loading="loading" :data="batches">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="batch_name" label="名称" />
        <el-table-column prop="category_name" label="类别" width="100" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="scan_image_count" label="扫描图片" width="100" />
        <el-table-column prop="import_total" label="总数" width="80" />
        <el-table-column prop="import_imported" label="已导入" width="80" />
        <el-table-column prop="import_duplicate" label="重复" width="80" />
        <el-table-column prop="import_failed" label="失败" width="80" />
        <el-table-column label="进度" width="220">
          <template #default="{ row }">
            <el-progress
              :percentage="progressFor(row)"
              :status="progressStatus(row)"
              :stroke-width="14"
            />
            <div class="progress-meta">{{ progressText(row) }}</div>
          </template>
        </el-table-column>
        <el-table-column label="导入速度" width="120">
          <template #default="{ row }">
            <span>{{ formatSpeed(row) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230">
          <template #default="{ row }">
            <el-button size="small" @click="showItems(row)">条目</el-button>
            <el-button size="small" type="warning" @click="retryBatch(row)">重试</el-button>
            <el-button size="small" type="danger" @click="stopBatch(row)">停止</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        layout="total, prev, pager, next"
        @current-change="() => loadBatches()"
      />
    </el-card>

    <el-dialog v-model="itemsVisible" title="导入条目" width="70%">
      <el-table v-loading="itemsLoading" :data="items">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="source_filename" label="文件名" />
        <el-table-column prop="normalized_relative_path" label="相对路径" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="sha256" label="SHA-256" width="180" />
        <el-table-column prop="error_detail" label="错误详情" />
      </el-table>
      <el-pagination
        v-model:current-page="itemsPagination.page"
        v-model:page-size="itemsPagination.page_size"
        :total="itemsPagination.total"
        layout="total, prev, pager, next"
        @current-change="() => showItems(currentBatch)"
      />
    </el-dialog>
  </el-container>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const batches = ref([])
const loading = ref(false)
const items = ref([])
const itemsLoading = ref(false)
const itemsVisible = ref(false)
const currentBatch = ref(null)

const pagination = reactive({ page: 1, page_size: 20, total: 0 })
const itemsPagination = reactive({ page: 1, page_size: 20, total: 0 })

const isActiveBatch = (batch) => ['queued', 'importing'].includes(batch?.status)
const hasActiveBatches = computed(() => batches.value.some(isActiveBatch))
let pollTimer = null

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

const progressFor = (batch) => {
  if (Number.isFinite(batch?.progress_percent)) {
    return batch.progress_percent
  }

  const total = progressTotal(batch)
  if (!total) {
    return 0
  }

  return Math.min(100, Math.round((progressProcessed(batch) / total) * 100))
}

const progressStatus = (batch) => {
  if (batch?.status === 'failed') return 'exception'
  if (batch?.status === 'partial') return 'warning'
  if (['completed', 'stopped'].includes(batch?.status)) return 'success'
  return ''
}

const progressText = (batch) => {
  switch (batch?.status) {
    case 'queued':
      return '等待处理'
    case 'importing':
      return `${progressProcessed(batch)} / ${progressTotal(batch)}`
    case 'completed':
      return '已完成'
    case 'partial':
      return `部分完成：${progressProcessed(batch)} / ${progressTotal(batch)}`
    case 'failed':
      return '导入失败'
    case 'stopped':
      return '已停止'
    case 'awaiting_confirmation':
      return '待确认'
    default:
      return batch?.status || '—'
  }
}

const formatSpeed = (batch) => {
  if (!['queued', 'importing'].includes(batch?.status)) {
    return '—'
  }

  const speed = Number(batch?.speed_per_second)
  if (Number.isFinite(speed) && speed > 0) {
    return `${speed.toFixed(1)} 张/秒`
  }

  return '—'
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
    const response = await axios.get('/api/assets/imports', {
      params: {
        page: pagination.page,
        page_size: pagination.page_size,
      },
    })
    batches.value = response.data.batches || []
    pagination.total = response.data.total || 0
  } catch (error) {
    if (!silent) {
      ElMessage.error('加载导入任务失败')
    }
  } finally {
    if (!silent) loading.value = false
    syncPolling()
  }
}

const showItems = async (batch) => {
  currentBatch.value = batch
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
    await axios.post(`/api/assets/imports/${batch.id}/retry`)
    ElMessage.success('已重新加入队列')
    loadBatches()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '重试失败')
  }
}

const stopBatch = async (batch) => {
  try {
    await axios.post(`/api/assets/imports/${batch.id}/stop`)
    ElMessage.success('已停止')
    loadBatches()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '停止失败')
  }
}

onMounted(loadBatches)
onBeforeUnmount(() => {
  if (pollTimer !== null) {
    clearInterval(pollTimer)
  }
})
</script>

<style scoped>
.import-records-page {
  display: block;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.progress-meta {
  margin-top: 4px;
  font-size: 12px;
  color: #909399;
  line-height: 1;
}
</style>
