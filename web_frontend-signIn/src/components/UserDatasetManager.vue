<template>
  <div class="app-container">
    <div class="dataset-section">
      <el-card class="dataset-card">
        <template #header>
          <div class="card-header">
            <span>My Datasets</span>
            <div class="header-actions">
              <el-input
                v-model="searchQuery"
                placeholder="Search by filename..."
                clearable
                @keyup.enter="searchDatasets"
                class="search-input"
              />
              <el-button type="primary" @click="searchDatasets">
                Search
              </el-button>
              <el-button type="primary" @click="fetchDatasets" :loading="loading">
                Refresh
              </el-button>
              <el-button type="primary" @click="dialogVisible = true">
                Upload
              </el-button>
            </div>
          </div>
        </template>
        <el-table v-loading="loading" :data="datasets" style="width: 100%">
          <el-table-column prop="filename" label="File Name" />
          <el-table-column label="Category" width="200">
            <template #default="scope">
              <div class="category-cell">
                <span :title="scope.row.category">{{ truncate(scope.row.category, 15) }}</span>
                <el-button type="primary" size="small" @click="showEditCategoryDialog(scope.row)">
                  Edit
                </el-button>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="Size" width="120">
            <template #default="scope">
              {{ formatSize(scope.row.size) }}
            </template>
          </el-table-column>
          <el-table-column label="Description" width="300">
            <template #default="scope">
              <div class="description-cell">
                <span :title="scope.row.description">{{ truncate_des(scope.row.description, 20) }}</span>
                <el-button type="primary" size="small" @click="showEditDialog(scope.row)">
                  Edit
                </el-button>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="Upload Date" width="180">
            <template #default="scope">
              {{ formatDate(scope.row.upload_date) }}
            </template>
          </el-table-column>
          <el-table-column label="Operations" width="200">
            <template #default="scope">
              <el-button type="danger" size="small" @click="deleteFile(scope.row.id)">
                Delete
              </el-button>
              <el-button type="primary" size="small" @click="downloadFile(scope.row.id)">
                Download
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
          style="margin-top: 20px; text-align: center;"
        />
      </el-card>
    </div>

    <!-- Upload Dataset Dialog -->
    <el-dialog
      title="Upload Dataset"
      v-model="dialogVisible"
      width="40%"
      :before-close="handleUploadDialogClose"
      destroy-on-close
    >
      <el-form :model="uploadForm" label-position="top" ref="uploadFormRef" :rules="uploadRules">
        <el-form-item label="File" prop="file">
          <el-upload
            drag
            :http-request="handleUpload"
            accept=".zip,.tar.gz,.rar"
            :multiple="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :auto-upload="false"
            class="wide-upload"
          >
            <el-icon class="el-icon--upload"><upload-filled /></el-icon>
            <div class="el-upload__text">
              Drop file here or <em>click to upload</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                Only .zip, .tar.gz or .rar files are supported (less 50G)
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="Category">
          <el-input
            v-model="uploadForm.category"
            placeholder="Enter a category (defaults to uncategorized)"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="Description">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            :rows="4"
            placeholder="Enter description"
          />
        </el-form-item>
        <div v-if="uploadStore.isUploading" class="upload-status">
          <el-progress
            :percentage="uploadStore.uploadProgress"
            :stroke-width="15"
            status="success"
            striped
          />
          <div class="progress-info">
            <span>{{ uploadStore.uploadProgress }}%</span>
            <span>{{ uploadStore.uploadSpeed }}</span>
          </div>
        </div>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button v-if="uploadStore.isUploading" @click="cancelUpload">Cancel Upload</el-button>
          <el-button @click="dialogVisible = false" :disabled="uploadStore.isUploading">
            Close
          </el-button>
          <el-button
            type="primary"
            @click="submitUpload"
            :disabled="!canSubmit || uploadStore.isUploading"
            :loading="uploadStore.isUploading"
          >
            Submit
          </el-button>
        </span>
      </template>
    </el-dialog>
    <!-- Edit Description Dialog -->
    <el-dialog title="Edit Description" v-model="editDialogVisible" width="30%" :before-close="handleClose">
      <el-input v-model="currentDescription" type="textarea" :rows="4" placeholder="Enter description" />
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="submitDescription" :loading="submitting">Submit</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Edit Category Dialog -->
    <el-dialog title="Edit Category" v-model="editCategoryDialogVisible" width="30%" :before-close="handleCategoryClose">
      <el-input
        v-model="currentCategory"
        placeholder="Enter category (defaults to uncategorized)"
      />
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editCategoryDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="submitCategory" :loading="submittingCategory">Submit</el-button>
        </span>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useUploadStore } from '@/stores/upload'

const authStore = useAuthStore()
const uploadStore = useUploadStore()

const uploadForm = ref({
  file: null,
  category: 'uncategorized',
  description: ''
})
const uploadFormRef = ref(null)
const datasets = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const submitting = ref(false)
const submittingCategory = ref(false)
const dialogVisible = ref(false)
const editDialogVisible = ref(false)
const editCategoryDialogVisible = ref(false)
const currentDescription = ref('')
const currentCategory = ref('')
const currentRow = ref(null)
const searchQuery = ref('')

const uploadRules = ref({
  file: [{ required: true, message: 'Please select a file', trigger: 'change' }]
})

const canSubmit = computed(() => {
  return uploadForm.value.file
})

const fetchDatasets = async () => {
  if (!authStore.token) {
    ElMessage.error('Please login to manage datasets')
    window.location.href = '/'
    return
  }
  try {
    loading.value = true
    const params = {
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (searchQuery.value) {
      params.filename_filter = searchQuery.value
    }
    const response = await axios.get('/api/my-datasets', {
      params,
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    datasets.value = response.data.datasets
    total.value = response.data.total
  } catch (error) {
    if (error.response?.status === 401) {
      ElMessage.error('Session expired, please login again')
      authStore.logout()
      window.location.href = '/'
    } else {
      ElMessage.error('Failed to fetch datasets: ' + (error.response?.data?.detail || error.message))
    }
  } finally {
    loading.value = false
  }
}

const searchDatasets = () => {
  currentPage.value = 1
  fetchDatasets()
}

const handlePageChange = (page) => {
  currentPage.value = page
  fetchDatasets()
}

const handleSizeChange = (size) => {
  pageSize.value = size
  currentPage.value = 1
  fetchDatasets()
}

const handleFileChange = (file) => {
  uploadForm.value.file = file.raw
}

const handleFileRemove = () => {
  uploadForm.value.file = null
}

const submitUpload = async () => {
  uploadFormRef.value.validate(async (valid) => {
    if (valid) {
      const formData = new FormData()
      formData.append('file', uploadForm.value.file)
      formData.append('category', uploadForm.value.category)
      formData.append('description', uploadForm.value.description || '')
      try {
        uploadStore.startUpload()
        const config = {
          headers: { 'Content-Type': 'multipart/form-data' },
          signal: uploadStore.controller.signal,
          onUploadProgress: (progressEvent) => {
            const { loaded, total } = progressEvent
            uploadStore.updateProgress(loaded, total)
          }
        }
        await axios.post('/api/upload', formData, config)
        ElMessage.success('Upload successful')
        uploadForm.value.file = null
        uploadForm.value.category = 'uncategorized'
        uploadForm.value.description = ''
        uploadFormRef.value.resetFields()
        dialogVisible.value = false
        fetchDatasets()
      } catch (error) {
        if (error.name === 'AbortError') {
          ElMessage.info('Upload canceled')
        } else {
          ElMessage.error(error.response?.data?.detail || 'Upload failed: ' + error.message)
        }
      } finally {
        uploadStore.finishUpload()
      }
    }
  })
}

const cancelUpload = () => {
  uploadStore.cancelUpload()
}

const handleUploadDialogClose = (done) => {
  if (uploadStore.isUploading) {
    ElMessageBox.confirm('An upload is in progress. Are you sure you want to cancel and close?')
      .then(() => {
        cancelUpload()
        done()
      })
      .catch(() => {})
  } else {
    ElMessageBox.confirm('Are you sure you want to close without uploading?')
      .then(() => done())
      .catch(() => {})
  }
}

const deleteFile = async (datasetId) => {
  try {
    await ElMessageBox.confirm('Are you sure you want to delete this dataset?', 'Warning', {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning'
    })
    loading.value = true
    await axios.delete(`/api/datasets/${datasetId}`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    ElMessage.success('Dataset deleted successfully')
    fetchDatasets()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || 'Failed to delete dataset')
    }
  } finally {
    loading.value = false
  }
}

const downloadFile = async (datasetId) => {
  try {
    window.location.href = `/api/download/${datasetId}`
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to download dataset')
  }
}

const showEditDialog = (row) => {
  currentRow.value = row
  currentDescription.value = row.description || ''
  editDialogVisible.value = true
}

const showEditCategoryDialog = (row) => {
  currentRow.value = row
  currentCategory.value = row.category || 'uncategorized'
  editCategoryDialogVisible.value = true
}

const submitDescription = async () => {
  try {
    submitting.value = true
    await axios.put(
      `/api/datasets/${currentRow.value.id}`,
      { description: currentDescription.value },
      { headers: { Authorization: `Bearer ${authStore.token}` } }
    )
    ElMessage.success('Description updated')
    editDialogVisible.value = false
    fetchDatasets()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to update description')
  } finally {
    submitting.value = false
  }
}

const submitCategory = async () => {
  try {
    submittingCategory.value = true
    await axios.put(
      `/api/datasets/${currentRow.value.id}`,
      { categories: currentCategory.value || '' },
      { headers: { Authorization: `Bearer ${authStore.token}` } }
    )
    ElMessage.success('Category updated')
    editCategoryDialogVisible.value = false
    fetchDatasets()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to update category')
  } finally {
    submittingCategory.value = false
  }
}

const handleClose = (done) => {
  ElMessageBox.confirm('Are you sure to close without saving?')
    .then(() => done())
    .catch(() => {})
}

const handleCategoryClose = (done) => {
  ElMessageBox.confirm('Are you sure to close without saving?')
    .then(() => done())
    .catch(() => {})
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const formatDate = (date) => {
  return new Date(date).toLocaleString()
}

const truncate = (text, length) => {
  if (!text) return 'uncategorized'
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

const truncate_des = (text, length) => {
  if (!text) return 'no description'
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

onMounted(() => {
  if (!authStore.currentUser || !authStore.token) {
    ElMessage.error('Please login to manage datasets')
    window.location.href = '/'
  } else {
    fetchDatasets()
  }
})
</script>

<style scoped>
.app-container {
  padding: 20px;
  margin-top: 0;
  height: calc(100vh - 40px);
  overflow-y: auto;
}

.dataset-section {
  width: 100%;
}

.dataset-card {
  width: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.wide-upload {
  width: 100%;
}

.wide-upload :deep(.el-upload-dragger) {
  width: 100%;
  padding: 20px;
  height: 200px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
}

.el-upload__text em {
  color: #409eff;
  font-style: normal;
}

.el-table .cell {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
}

.description-cell {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0 10px;
}

.description-cell span {
  flex-grow: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.category-cell {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0 10px;
}

.category-cell span {
  flex-grow: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.el-button--small {
  padding: 6px 12px;
}

.search-input {
  width: 200px;
  margin-right: 10px;
}

.el-button--primary {
  background-color: #409eff;
  border-color: #409eff;
  color: #fff;
}

.el-button--primary:hover {
  background-color: #66b1ff;
  border-color: #66b1ff;
}

.upload-status {
  margin-top: 10px;
  text-align: center;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-top: 5px;
  font-size: 14px;
  color: #606266;
}

.dialog-footer {
  display: flex;
  gap: 10px;
}
</style>
