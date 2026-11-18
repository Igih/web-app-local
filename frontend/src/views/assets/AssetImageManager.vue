<template>
  <el-container class="asset-image-page">
    <el-card>
      <template #header>
        <div class="page-header">
          <span>图像资源管理</span>
          <div>
            <el-button @click="$router.push('/assets/import')">新建导入</el-button>
            <el-button type="primary" @click="loadImages">刷新</el-button>
          </div>
        </div>
      </template>

      <el-form inline @submit.prevent="loadImages">
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
          <el-input v-model="filters.tags" placeholder="逗号分隔" />
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

      <el-button
        v-if="selectedRows.length"
        type="warning"
        @click="openBatchEdit"
      >
        批量修改
      </el-button>

      <el-table v-loading="loading" :data="images" @selection-change="onSelectionChange">
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
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <el-button size="small" @click="showDetail(row.id)">详情</el-button>
            <el-button size="small" type="primary" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.page_size"
        :total="pagination.total"
        :page-sizes="[20, 50, 100]"
        layout="total, sizes, prev, pager, next"
        @current-change="loadImages"
        @size-change="loadImages"
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
  </el-container>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  batchUpdateAssetImages,
  getAssetCategories,
  getAssetImage,
  getAssetImageThumbnail,
  listAssetImages,
  updateAssetImage,
} from '@/services/assetService'

const categories = ref([])
const images = ref([])
const thumbnailUrls = reactive({})
const loading = ref(false)
const selectedRows = ref([])
const detail = ref(null)
const detailVisible = ref(false)
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
  tags: '',
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

const typeLabel = (value) => ({ photo: '实拍', hand_drawn: '手绘' }[value] || '未指定')
const spectralLabel = (value) => ({ visible: '可见光', infrared: '红外' }[value] || '未指定')

const loadImages = async () => {
  loading.value = true
  try {
    const result = await listAssetImages({
      ...filters,
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
  try {
    categories.value = await getAssetCategories()
  } catch (error) {
    ElMessage.error('加载类别失败')
  }
  loadImages()
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

.thumb {
  width: 64px;
  height: 64px;
  object-fit: cover;
  border-radius: 4px;
}

.thumb-placeholder {
  background: #f0f0f0;
}
</style>
