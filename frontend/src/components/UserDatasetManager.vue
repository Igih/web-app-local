<template>
  <div class="app-container bg-gray-100 min-h-screen p-6">
    <!-- Pending Uploads Section -->
    <div class="dataset-section mb-6">
      <el-card class="dataset-card shadow-lg">
        <template #header>
          <div class="card-header flex justify-between items-center">
            <div class="flex items-center gap-2">
              <span class="text-xl font-semibold text-gray-800">Pending Uploads</span>
              <span class="text-sm text-gray-500">
                (note: scp sources app@12.1.1.73:/data/datasets/pending_uploads/{{ authStore.currentUser.username }})
              </span>
            </div>
            <el-button type="primary" @click="fetchPendingUploads" :loading="pendingLoading">
              Refresh
            </el-button>
          </div>
        </template>
        <el-table v-loading="pendingLoading" :data="pendingFiles" style="width: 100%">
          <el-table-column prop="filename" label="File Name" />
          <el-table-column label="Size" width="120">
            <template #default="scope">
              {{ formatSize(scope.row.size) }}
            </template>
          </el-table-column>
          <el-table-column label="Operations" width="200">
            <template #default="scope">
              <el-button type="primary" size="small" @click="showPendingUploadDialog(scope.row)">
                Upload
              </el-button>
              <el-button type="danger" size="small" @click="deletePendingFile(scope.row.filename)">
                Delete
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- My Datasets Section -->
    <div class="dataset-section">
      <el-card class="dataset-card shadow-lg">
        <template #header>
          <div class="card-header flex justify-between items-center">
            <span class="text-xl font-semibold text-gray-800">My Datasets</span>
            <div class="header-actions flex items-center gap-4">
              <el-input
                v-model="searchQuery"
                placeholder="Search by filename..."
                clearable
                @keyup.enter="searchDatasets"
                class="w-64"
              />
              <el-button type="primary" @click="searchDatasets">
                Search
              </el-button>
              <el-button type="primary" @click="dialogVisible = true">
                Upload
              </el-button>
              <el-button type="primary" @click="fetchDatasets" :loading="loading">
                Refresh
              </el-button>
            </div>
          </div>
        </template>
        <el-table v-loading="loading" :data="datasets" style="width: 100%">
          <el-table-column label="File Name">
            <template #default="scope">
              <div class="filename-cell">
                <span :title="scope.row.filename">{{ scope.row.filename }}</span>
                <el-button type="primary" size="small" @click="showEditFilenameDialog(scope.row)">
                  Edit
                </el-button>
              </div>
            </template>
          </el-table-column>
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
          class="mt-6 text-center"
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
                Only .zip, .tar.gz or .rar files are supported (limit 50G)
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="Category">
          <el-input
            v-model="uploadForm.category"
            placeholder="class 1 、class 1、class 3..."
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
          <div class="progress-info flex justify-between mt-2 text-sm text-gray-600">
            <span>{{ uploadStore.uploadProgress }}%</span>
            <span>{{ uploadStore.uploadSpeed }}</span>
          </div>
        </div>
      </el-form>
      <template #footer>
        <span class="dialog-footer flex gap-4">
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

    <!-- Pending Upload Dialog -->
    <el-dialog
      title="Upload Pending File"
      v-model="pendingUploadDialogVisible"
      width="40%"
      :before-close="handlePendingUploadDialogClose"
      destroy-on-close
    >
      <el-form :model="pendingUploadForm" label-position="top" ref="pendingUploadFormRef">
        <el-form-item label="File Name">
          <el-input
            v-model="pendingUploadForm.filename"
            disabled
          />
        </el-form-item>
        <el-form-item label="Category">
          <el-input
            v-model="pendingUploadForm.category"
            placeholder="class 1 、class 1、class 3..."
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item label="Description">
          <el-input
            v-model="pendingUploadForm.description"
            type="textarea"
            :rows="4"
            placeholder="Enter description"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer flex gap-4">
          <el-button @click="pendingUploadDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="submitPendingUpload" :loading="submittingPending">
            Submit
          </el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Edit Description Dialog -->
    <el-dialog title="Edit Description" v-model="editDialogVisible" width="30%" :before-close="handleClose">
      <el-input v-model="currentDescription" type="textarea" :rows="16" placeholder="Enter description" />
      <template #footer>
        <span class="dialog-footer flex gap-4">
          <el-button @click="editDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="submitDescription" :loading="submitting">Submit</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Edit Category Dialog -->
    <el-dialog title="Edit Category" v-model="editCategoryDialogVisible" width="30%" :before-close="handleCategoryClose">
      <el-input
        v-model="currentCategory"
        placeholder="class 1 、class 1、class 3..."
      />
      <template #footer>
        <span class="dialog-footer flex gap-4">
          <el-button @click="editCategoryDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="submitCategory" :loading="submittingCategory">Submit</el-button>
        </span>
      </template>
    </el-dialog>
    <!-- Edit Filename Dialog -->
    <el-dialog title="Edit Filename" v-model="editFilenameDialogVisible" width="30%" :before-close="handleFilenameClose">
      <el-form 
        :model="{ currentFilename }" 
        :rules="filenameRules" 
        ref="filenameFormRef" 
        label-position="top"
        @submit.prevent
      >
        <el-form-item label="New Filename" prop="currentFilename">
          <el-input
            v-model="currentFilename"
            placeholder="Enter new filename (extension will be preserved)"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer flex gap-4">
          <el-button @click="editFilenameDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="submitFilename" :loading="submittingFilename">Submit</el-button>
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
  category: 'class 1 、class 1、class 3...',
  description: ''
})
const pendingUploadForm = ref({
  filename: '',
  category: 'class 1 、class 1、class 3...',
  description: ''
})
const uploadFormRef = ref(null)
const pendingUploadFormRef = ref(null)
const datasets = ref([])
const pendingFiles = ref([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const loading = ref(false)
const pendingLoading = ref(false)
const submitting = ref(false)
const submittingCategory = ref(false)
const submittingPending = ref(false)
const dialogVisible = ref(false)
const editDialogVisible = ref(false)
const editCategoryDialogVisible = ref(false)
const pendingUploadDialogVisible = ref(false)
const currentDescription = ref('')
const currentCategory = ref('')
const currentRow = ref(null)
const searchQuery = ref('')
const editFilenameDialogVisible = ref(false)
const currentFilename = ref('')
const submittingFilename = ref(false)

const uploadRules = ref({
  file: [{ required: true, message: 'Please select a file', trigger: 'change' }]
})

const filenameFormRef = ref(null)
const filenameRules = ref({
  currentFilename: [
    { required: true, message: 'Please enter a filename', trigger: 'blur' }
  ]
})

const showEditFilenameDialog = (row) => {
  currentRow.value = row
  // Display filename without suffix
  currentFilename.value = row.filename.replace(/\.(zip|tar\.gz|rar)$/i, '')
  editFilenameDialogVisible.value = true
}

const submitFilename = async () => {
  filenameFormRef.value.validate(async (valid) => {
    if (valid) {
      try {
        submittingFilename.value = true
        // Append original suffix to the entered filename
        const originalSuffix = currentRow.value.filename.match(/\.(zip|tar\.gz|rar)$/i)?.[0]
        if (!originalSuffix) {
          ElMessage.error('Original filename has an invalid extension')
          return
        }
        const newFilename = currentFilename.value + originalSuffix
        await axios.put(
          `/api/datasets/${currentRow.value.id}`,
          { filename: newFilename },
          { headers: { Authorization: `Bearer ${authStore.token}` } }
        )
        ElMessage.success('Filename updated')
        editFilenameDialogVisible.value = false
        fetchDatasets()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || 'Failed to update filename')
      } finally {
        submittingFilename.value = false
      }
    }
  })
}

const handleFilenameClose = (done) => {
  ElMessageBox.confirm('Are you sure to close without saving?')
    .then(() => done())
    .catch(() => {})
}

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

const fetchPendingUploads = async () => {
  if (!authStore.token) {
    ElMessage.error('Please login to manage datasets')
    window.location.href = '/'
    return
  }
  try {
    pendingLoading.value = true
    const response = await axios.get('/api/pending-uploads', {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    pendingFiles.value = response.data.files
  } catch (error) {
    ElMessage.error('Failed to fetch pending uploads: ' + (error.response?.data?.detail || error.message))
  } finally {
    pendingLoading.value = false
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
        uploadForm.value.category = 'class 1 、class 1、class 3...'
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

const showPendingUploadDialog = (row) => {
  pendingUploadForm.value.filename = row.filename
  pendingUploadForm.value.category = 'class 1 、class 1、class 3...'
  pendingUploadForm.value.description = ''
  pendingUploadDialogVisible.value = true
}

const submitPendingUpload = async () => {
  try {
    submittingPending.value = true
    const formData = new FormData()
    formData.append('filename', pendingUploadForm.value.filename)
    formData.append('category', pendingUploadForm.value.category)
    formData.append('description', pendingUploadForm.value.description || '')
    await axios.post('/api/upload-from-pending', formData, {
      headers: {
        Authorization: `Bearer ${authStore.token}`,
        'Content-Type': 'multipart/form-data'
      }
    })
    ElMessage.success('Pending file uploaded successfully')
    pendingUploadDialogVisible.value = false
    fetchDatasets()
    fetchPendingUploads()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to upload pending file')
  } finally {
    submittingPending.value = false
  }
}

const handlePendingUploadDialogClose = (done) => {
  ElMessageBox.confirm('Are you sure you want to close without uploading?')
    .then(() => done())
    .catch(() => {})
}

const deletePendingFile = async (filename) => {
  try {
    await ElMessageBox.confirm('Are you sure you want to delete this pending file?', 'Warning', {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning'
    })
    await axios.delete(`/api/pending-uploads/${filename}`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    ElMessage.success('Pending file deleted successfully')
    fetchPendingUploads()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || 'Failed to delete pending file')
    }
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
  currentCategory.value = row.category || 'class 1 、class 1、class 3...'
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
  if (!text) return 'class 1 、class 1、class 3...'
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
    fetchPendingUploads()
  }
})
</script>

<style scoped>
.app-container {
  background-color: #f3f4f6;
  min-height: 100vh;
  padding: 1.5rem;
}

.dataset-section {
  width: 100%;
  margin-bottom: 1.5rem;
}

.dataset-card {
  width: 100%;
  background-color: #ffffff;
  border-radius: 0.5rem;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 1rem;
}

.wide-upload {
  width: 100%;
}

.wide-upload :deep(.el-upload-dragger) {
  width: 100%;
  padding: 1.25rem;
  height: 12rem;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  border: 2px dashed #d1d5db;
  border-radius: 0.5rem;
}

.el-upload__text em {
  color: #3b82f6;
  font-weight: 500;
}

.el-table .cell {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 0.5rem;
}

.description-cell {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0 0.5rem;
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
  padding: 0 0.5rem;
}

.category-cell span {
  flex-grow: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.filename-cell {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0 0.5rem;
}

.filename-cell span {
  flex-grow: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.el-button--small {
  padding: 0.375rem 0.75rem;
  font-size: 0.875rem;
}

.search-input {
  width: 16rem;
  margin-right: 1rem;
}

.el-button--primary {
  background-color: #3b82f6;
  border-color: #3b82f6;
  color: #ffffff;
}

.el-button--primary:hover {
  background-color: #2563eb;
  border-color: #2563eb;
}

.upload-status {
  margin-top: 1rem;
  text-align: center;
}

.progress-info {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #4b5563;
}

.dialog-footer {
  display: flex;
  gap: 10px;
}

.header-actions {
  display: flex;
  flex-direction: row; /* 明确指定水平排列 */
  align-items: center;
  gap: 1rem;
}

/* 确保输入框和按钮的宽度和显示方式正确 */
.w-64 {
  width: 16rem !important; /* 确保输入框宽度固定 */
  flex-shrink: 0; /* 防止输入框被压缩 */
}

/* 防止按钮换行 */
.el-button {
  white-space: nowrap;
}
</style>