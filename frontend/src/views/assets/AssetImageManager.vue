<template>
  <el-container class="asset-image-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <span>图像资源管理</span>
          <div class="header-actions">
            <el-radio-group v-model="viewMode" size="small" @change="onViewModeChange">
              <el-radio-button label="grid">缩略图</el-radio-button>
              <el-radio-button label="list">列表</el-radio-button>
            </el-radio-group>
            <el-button @click="$router.push('/assets/import')">新建导入</el-button>
            <el-button type="primary" :disabled="!hasSearched" :loading="loading" @click="loadImages">刷新</el-button>
          </div>
        </div>
      </template>

      <el-form class="filter-form" inline @submit.prevent="submitSearch">
        <el-form-item label="类别">
          <el-select v-model="filters.category" clearable placeholder="全部">
            <el-option
              v-for="category in categories"
              :key="category.id"
              :label="category.display_name"
              :value="category.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="一级类型">
          <el-select v-model="filters.capture_type" clearable placeholder="全部">
            <el-option label="实拍" value="photo" />
            <el-option label="手绘" value="hand_drawn" />
            <el-option label="未指定" value="unspecified" />
          </el-select>
        </el-form-item>
        <el-form-item label="二级类型">
          <el-select v-model="filters.spectral_type" clearable placeholder="全部">
            <el-option label="可见光" value="visible" />
            <el-option label="红外" value="infrared" />
            <el-option label="未指定" value="unspecified" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            class="filter-tags"
            v-model="filters.tags"
            multiple
            filterable
            clearable
            :multiple-limit="5"
            placeholder="请选择标签"
          >
            <el-option
              v-for="tag in tagOptions"
              :key="tag.id"
              :label="tag.display_name"
              :value="tag.normalized_name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="标签模式">
          <el-radio-group v-model="filters.tag_mode">
            <el-radio-button label="and">AND</el-radio-button>
            <el-radio-button label="or">OR</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" clearable placeholder="全部">
            <el-option label="Ready" value="ready" />
            <el-option label="Pending" value="pending" />
            <el-option label="Quarantined" value="quarantined" />
            <el-option label="Failed" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="最小宽">
          <el-input-number v-model="filters.min_width" :min="0" />
        </el-form-item>
        <el-form-item label="最小高">
          <el-input-number v-model="filters.min_height" :min="0" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" native-type="submit">查询</el-button>
        </el-form-item>
      </el-form>

      <div v-if="viewMode === 'list' && selectedRows.length" class="batch-actions">
        <el-button type="warning" @click="openBatchEdit">
          批量修改
        </el-button>
        <el-button type="danger" @click="openBatchDelete">
          批量删除
        </el-button>
      </div>

      <template v-if="viewMode === 'list'">
        <el-table v-loading="loading" :data="images" :empty-text="emptyDescription" @selection-change="onSelectionChange">
          <el-table-column type="selection" width="45" />
          <el-table-column label="缩略图" width="90">
            <template #default="{ row }">
              <img
                v-if="thumbnailUrls[row.id]"
                :src="thumbnailUrls[row.id]"
                class="thumb"
                alt=""
              />
              <div v-else class="thumb thumb-placeholder"></div>
            </template>
          </el-table-column>
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="category_name" label="类别" width="100" />
          <el-table-column label="一级类型" width="100">
            <template #default="{ row }">{{ typeLabel(row.capture_type) }}</template>
          </el-table-column>
          <el-table-column label="二级类型" width="100">
            <template #default="{ row }">{{ spectralLabel(row.spectral_type) }}</template>
          </el-table-column>
          <el-table-column label="尺寸" width="130">
            <template #default="{ row }">{{ row.width }} x {{ row.height }}</template>
          </el-table-column>
          <el-table-column prop="file_format" label="格式" width="80" />
          <el-table-column label="标签">
            <template #default="{ row }">{{ (row.tags || []).join(', ') }}</template>
          </el-table-column>
          <el-table-column label="操作" width="230">
            <template #default="{ row }">
              <el-button size="small" @click="showDetail(row.id)">详情</el-button>
              <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" type="danger" @click="confirmDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </template>
      <template v-else>
        <div v-loading="loading" class="thumbnail-grid-panel">
          <el-empty v-if="!loading && !images.length" :description="emptyDescription" />
          <div v-else-if="images.length" class="thumbnail-grid">
            <div
              v-for="(row, index) in images"
              :key="row.id"
              class="thumbnail-card"
              @click="openPreview(index)"
            >
              <img
                v-if="thumbnailUrls[row.id]"
                :src="thumbnailUrls[row.id]"
                class="grid-thumb"
                alt=""
              />
              <div v-else class="grid-thumb grid-thumb-placeholder"></div>
            </div>
          </div>
        </div>
      </template>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </el-card>

    <el-dialog v-model="detailVisible" title="图片详情" width="60%">
      <el-descriptions v-if="detail" :column="2" border>
        <el-descriptions-item label="ID">{{ detail.id }}</el-descriptions-item>
        <el-descriptions-item label="类别">{{ detail.category_name }}</el-descriptions-item>
        <el-descriptions-item label="一级类型">{{ typeLabel(detail.capture_type) }}</el-descriptions-item>
        <el-descriptions-item label="二级类型">{{ spectralLabel(detail.spectral_type) }}</el-descriptions-item>
        <el-descriptions-item label="尺寸">{{ detail.width }} x {{ detail.height }}</el-descriptions-item>
        <el-descriptions-item label="SHA-256">{{ detail.sha256 }}</el-descriptions-item>
      </el-descriptions>
      <div v-if="detail?.sources?.length">
        <h4>来源文件</h4>
        <el-table :data="detail.sources">
          <el-table-column prop="source_path" label="原路径" />
          <el-table-column prop="source_filename" label="原文件名" />
          <el-table-column prop="relative_path" label="相对路径" />
          <el-table-column prop="source_machine" label="来源机器" />
        </el-table>
      </div>
    </el-dialog>

    <el-dialog v-model="editVisible" title="编辑图片" width="40%">
      <el-form v-if="editForm" label-width="100px">
        <el-form-item label="类别">
          <el-select v-model="editForm.category" clearable>
            <el-option
              v-for="category in categories"
              :key="category.id"
              :label="category.display_name"
              :value="category.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="一级类型">
          <el-select v-model="editForm.capture_type" clearable>
            <el-option label="实拍" value="photo" />
            <el-option label="手绘" value="hand_drawn" />
          </el-select>
        </el-form-item>
        <el-form-item label="二级类型">
          <el-select v-model="editForm.spectral_type" clearable :disabled="!editForm.capture_type">
            <el-option label="可见光" value="visible" />
            <el-option label="红外" value="infrared" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select
            v-model="editForm.tags"
            multiple
            filterable
            allow-create
            :multiple-limit="5"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="batchVisible" title="批量修改" width="40%">
      <el-form label-width="100px">
        <el-form-item label="类别">
          <el-select v-model="batchForm.category" clearable>
            <el-option
              v-for="category in categories"
              :key="category.id"
              :label="category.display_name"
              :value="category.name"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="一级类型">
          <el-select v-model="batchForm.capture_type" clearable>
            <el-option label="实拍" value="photo" />
            <el-option label="手绘" value="hand_drawn" />
          </el-select>
        </el-form-item>
        <el-form-item label="二级类型">
          <el-select v-model="batchForm.spectral_type" clearable :disabled="!batchForm.capture_type">
            <el-option label="可见光" value="visible" />
            <el-option label="红外" value="infrared" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchVisible = false">取消</el-button>
        <el-button type="warning" @click="saveBatch">应用</el-button>
      </template>
    </el-dialog>

    <div v-if="previewVisible" class="asset-image-preview-modal" @click="closePreview">
      <div class="asset-image-preview-content" @click.stop>
        <button class="preview-close" @click="closePreview">×</button>
        <button
          class="preview-nav-arrow preview-nav-left"
          :disabled="previewIndex <= 0"
          @click.stop="movePreview(-1)"
        >
          ◀
        </button>
        <img
          v-if="previewOriginalUrl"
          :src="previewOriginalUrl"
          class="preview-full-image"
          alt=""
        />
        <div v-else class="preview-image-placeholder">图片加载中...</div>
        <button
          class="preview-nav-arrow preview-nav-right"
          :disabled="previewIndex >= images.length - 1"
          @click.stop="movePreview(1)"
        >
          ▶
        </button>
      </div>
    </div>
  </el-container>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  batchDeleteAssetImages,
  batchUpdateAssetImages,
  deleteAssetImage,
  getAssetCategories,
  getAssetImage,
  getAssetImageOriginal,
  getAssetImageThumbnail,
  getAssetTags,
  listAssetImages,
  updateAssetImage,
} from '@/services/assetService'

const categories = ref([])
const tagOptions = ref([])
const viewMode = ref('grid')
const hasSearched = ref(false)
const submittedFilters = ref(null)
const images = ref([])
const thumbnailUrls = reactive({})
const originalUrls = reactive({})
const loading = ref(false)
const selectedRows = ref([])
const detail = ref(null)
const detailVisible = ref(false)
const previewVisible = ref(false)
const previewIndex = ref(-1)
const previewOriginalUrl = ref('')
const previewLoading = ref(false)
const editVisible = ref(false)
const editForm = ref(null)
const batchVisible = ref(false)
const batchForm = reactive({
  image_ids: [],
  category: '',
  capture_type: '',
  spectral_type: '',
  tags: null,
})

const filters = reactive({
  category: '',
  capture_type: '',
  spectral_type: '',
  tags: [],
  tag_mode: 'and',
  status: '',
  min_width: null,
  min_height: null,
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0,
})

const emptyDescription = computed(() =>
  hasSearched.value ? '未找到符合条件的图片' : '设置筛选条件后点击查询'
)
const currentPreviewImage = computed(() => images.value[previewIndex.value] || null)

const typeLabel = (value) => ({ photo: '实拍', hand_drawn: '手绘' }[value] || '未指定')
const spectralLabel = (value) => ({ visible: '可见光', infrared: '红外' }[value] || '未指定')

const loadImages = async () => {
  if (!submittedFilters.value) {
    return
  }

  loading.value = true
  hasSearched.value = true
  try {
    const result = await listAssetImages({
      ...submittedFilters.value,
      page: pagination.page,
      page_size: pagination.page_size,
    })
    images.value = result.images || []
    pagination.total = result.total || 0
    loadThumbnails()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载图片失败')
  } finally {
    loading.value = false
  }
}

const submitSearch = () => {
  submittedFilters.value = {
    ...filters,
    tags: filters.tags.join(','),
  }
  pagination.page = 1
  loadImages()
}

const handlePageChange = () => {
  loadImages()
}

const handleSizeChange = () => {
  pagination.page = 1
  loadImages()
}

const loadThumbnails = () => {
  images.value.forEach((row) => {
    if (thumbnailUrls[row.id]) {
      return
    }
    getAssetImageThumbnail(row.id)
      .then((url) => {
        thumbnailUrls[row.id] = url
      })
      .catch((error) => {
        console.warn(`加载图片 ${row.id} 缩略图失败`, error)
      })
  })
}

const onViewModeChange = () => {
  selectedRows.value = []
  previewVisible.value = false
}

const getOriginalUrl = async (imageId) => {
  if (originalUrls[imageId]) {
    return originalUrls[imageId]
  }

  const url = await getAssetImageOriginal(imageId)
  originalUrls[imageId] = url
  return url
}

const loadPreviewData = async () => {
  const row = currentPreviewImage.value
  if (!row) {
    return
  }

  previewLoading.value = true
  previewOriginalUrl.value = ''

  try {
    previewOriginalUrl.value = await getOriginalUrl(row.id)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载原图失败')
  } finally {
    previewLoading.value = false
  }
}

const openPreview = (index) => {
  previewIndex.value = index
  previewVisible.value = true
  loadPreviewData()
}

const movePreview = (delta) => {
  const nextIndex = previewIndex.value + delta
  if (nextIndex < 0 || nextIndex >= images.value.length) {
    return
  }

  previewIndex.value = nextIndex
  loadPreviewData()
}

const closePreview = () => {
  previewVisible.value = false
}

const handlePreviewKeydown = (event) => {
  if (!previewVisible.value) {
    return
  }

  if (event.key === 'Escape') {
    closePreview()
    return
  }

  if (event.key === 'ArrowLeft') {
    movePreview(-1)
  }
  if (event.key === 'ArrowRight') {
    movePreview(1)
  }
}

const showDetail = async (imageId) => {
  try {
    detail.value = await getAssetImage(imageId)
    detailVisible.value = true
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '加载详情失败')
  }
}

const openEdit = async (row) => {
  editForm.value = {
    id: row.id,
    category: row.category_name,
    capture_type: row.capture_type || '',
    spectral_type: row.spectral_type || '',
    tags: (row.tags || []).slice(),
  }
  editVisible.value = true
}

const saveEdit = async () => {
  try {
    const payload = {
      category: editForm.value.category || null,
      capture_type: editForm.value.capture_type || null,
      spectral_type: editForm.value.spectral_type || null,
      tags: editForm.value.tags,
    }
    await updateAssetImage(editForm.value.id, payload)
    ElMessage.success('保存成功')
    editVisible.value = false
    loadImages()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  }
}

const onSelectionChange = (rows) => {
  selectedRows.value = rows
}

const openBatchEdit = () => {
  batchForm.image_ids = selectedRows.value.map((row) => row.id)
  batchVisible.value = true
}

const cleanupImageUrls = (imageIds) => {
  imageIds.forEach((imageId) => {
    if (thumbnailUrls[imageId]) {
      URL.revokeObjectURL(thumbnailUrls[imageId])
      delete thumbnailUrls[imageId]
    }
    if (originalUrls[imageId]) {
      URL.revokeObjectURL(originalUrls[imageId])
      delete originalUrls[imageId]
    }
  })
}

const reloadAfterDelete = (deletedCount) => {
  if (deletedCount >= images.value.length && pagination.page > 1) {
    pagination.page -= 1
  }
  loadImages()
}

const confirmDelete = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确认删除图片 ID ${row.id} 吗？原图和缩略图文件也会被删除。`,
      '删除确认',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      }
    )
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return
    }
    ElMessage.error(error.response?.data?.detail || '取消失败')
    return
  }

  try {
    await deleteAssetImage(row.id)
    ElMessage.success('删除成功')
    selectedRows.value = selectedRows.value.filter((item) => item.id !== row.id)
    cleanupImageUrls([row.id])
    reloadAfterDelete(1)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '删除失败')
  }
}

const openBatchDelete = async () => {
  const imageIds = selectedRows.value.map((row) => row.id)
  if (!imageIds.length) {
    return
  }

  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${imageIds.length} 张图片吗？原图和缩略图文件也会被删除。`,
      '批量删除确认',
      {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
      }
    )
  } catch (error) {
    if (error === 'cancel' || error === 'close') {
      return
    }
    ElMessage.error(error.response?.data?.detail || '取消失败')
    return
  }

  try {
    await batchDeleteAssetImages(imageIds)
    ElMessage.success(`已删除 ${imageIds.length} 张图片`)
    cleanupImageUrls(imageIds)
    selectedRows.value = []
    reloadAfterDelete(imageIds.length)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '批量删除失败')
  }
}

const saveBatch = async () => {
  try {
    const payload = {
      image_ids: batchForm.image_ids,
      category: batchForm.category || null,
      capture_type: batchForm.capture_type || null,
      spectral_type: batchForm.spectral_type || null,
    }
    await batchUpdateAssetImages(payload)
    ElMessage.success('批量更新成功')
    batchVisible.value = false
    loadImages()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '批量更新失败')
  }
}

onMounted(async () => {
  window.addEventListener('keydown', handlePreviewKeydown)

  try {
    categories.value = await getAssetCategories()
  } catch (error) {
    ElMessage.error('加载类别失败')
  }

  try {
    tagOptions.value = await getAssetTags()
  } catch (error) {
    ElMessage.error('加载标签失败')
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handlePreviewKeydown)
  Object.values(thumbnailUrls).forEach((url) => URL.revokeObjectURL(url))
  Object.values(originalUrls).forEach((url) => URL.revokeObjectURL(url))
})
</script>

<style scoped>
.asset-image-page {
  display: block;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.filter-form :deep(.el-select) {
  width: 180px;
}

.filter-form :deep(.filter-tags) {
  width: 220px;
}

.thumb {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 4px;
}

.thumb-placeholder {
  background: #f0f0f0;
}

.thumbnail-grid-panel {
  min-height: 260px;
}

.thumbnail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.thumbnail-card {
  aspect-ratio: 1;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f5f7fa;
  cursor: pointer;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.thumbnail-card:hover {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.14);
  transform: translateY(-2px);
}

.grid-thumb {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
}

.grid-thumb-placeholder {
  background: #e5e7eb;
}

.asset-image-preview-modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.82);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  overflow: auto;
}

.asset-image-preview-content {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 160px;
  min-height: 160px;
}

.preview-full-image {
  display: block;
  max-width: 90vw;
  max-height: 90vh;
  object-fit: contain;
}

.preview-image-placeholder {
  color: #fff;
  font-size: 16px;
}

.preview-close {
  position: fixed;
  top: 18px;
  right: 24px;
  z-index: 2;
  width: 36px;
  height: 36px;
  border: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.preview-close:hover {
  background: rgba(255, 255, 255, 0.32);
}

.preview-nav-arrow {
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  z-index: 2;
  width: 46px;
  height: 64px;
  border: none;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  font-size: 24px;
  cursor: pointer;
}

.preview-nav-arrow:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.32);
}

.preview-nav-arrow:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.preview-nav-left {
  left: 22px;
}

.preview-nav-right {
  right: 22px;
}
</style>
