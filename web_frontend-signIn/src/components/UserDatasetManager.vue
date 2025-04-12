<template>
    <el-container class="app-container">
      <el-main>
        <el-card class="upload-card">
          <template #header>
            <div class="card-header">
              <span>Upload Dataset</span>
            </div>
          </template>
          <el-form :model="uploadForm" label-position="top">
            <el-form-item label="Category">
              <el-input v-model="uploadForm.category" placeholder="Enter category (e.g., plane)" />
            </el-form-item>
            <el-form-item label="Description">
              <el-input
                v-model="uploadForm.description"
                type="textarea"
                :rows="4"
                placeholder="Enter description"
              />
            </el-form-item>
            <el-form-item label="File">
              <el-upload
                drag
                :http-request="handleUpload"
                accept=".zip,.tar.gz"
                :multiple="false"
              >
                <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                <div class="el-upload__text">
                  Drop file here or <em>click to upload</em>
                </div>
                <template #tip>
                  <div class="el-upload__tip">
                    Only .zip or .tar.gz files are supported
                  </div>
                </template>
              </el-upload>
            </el-form-item>
          </el-form>
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
          <el-button v-if="uploadStore.isUploading" @click="cancelUpload">Cancel Upload</el-button>
        </el-card>
  
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
              </div>
            </div>
          </template>
          <el-table v-loading="loading" :data="datasets" style="width: 100%">
            <el-table-column prop="filename" label="File Name" />
            <el-table-column prop="category" label="Category" width="150" />
            <el-table-column label="Size" width="120">
              <template #default="scope">
                {{ formatSize(scope.row.size) }}
              </template>
            </el-table-column>
            <el-table-column label="Description" width="300">
              <template #default="scope">
                <div class="description-cell">
                  <span :title="scope.row.description">{{ truncate(scope.row.description, 20) }}</span>
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
  
        <el-dialog title="Edit Description" v-model="dialogVisible" width="30%" :before-close="handleClose">
          <el-input v-model="currentDescription" type="textarea" :rows="4" placeholder="Enter description" />
          <template #footer>
            <span class="dialog-footer">
              <el-button @click="dialogVisible = false">Cancel</el-button>
              <el-button type="primary" @click="submitDescription" :loading="submitting">Submit</el-button>
            </span>
          </template>
        </el-dialog>
      </el-main>
    </el-container>
  </template>
  
  <script setup>
  import { ref, onMounted } from 'vue'
  import { UploadFilled } from '@element-plus/icons-vue'
  import axios from 'axios'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import { useAuthStore } from '@/stores/auth'
  import { useUploadStore } from '@/stores/upload'
  
  const authStore = useAuthStore()
  const uploadStore = useUploadStore()
  
  const uploadForm = ref({
    category: '',
    description: ''
  })
  const datasets = ref([])
  const total = ref(0)
  const currentPage = ref(1)
  const pageSize = ref(10)
  const loading = ref(false)
  const submitting = ref(false)
  const dialogVisible = ref(false)
  const currentDescription = ref('')
  const currentRow = ref(null)
  const searchQuery = ref('')
  
  const fetchDatasets = async () => {
  console.log('Token:', authStore.token); // 调试：打印 token
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
      headers: {
        Authorization: `Bearer ${authStore.token}` // 使用 authStore.token
      }
    })
    datasets.value = response.data.datasets
    total.value = response.data.total
  } catch (error) {
    console.log('Error:', error.response); // 调试：打印错误详情
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
  
  const handleUpload = async (options) => {
    if (!uploadForm.value.category) {
      ElMessage.error('Category is required')
      return
    }
    const file = options.file
    const formData = new FormData()
    formData.append('file', file)
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
      uploadForm.value.category = ''
      uploadForm.value.description = ''
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
  
  const cancelUpload = () => {
    uploadStore.cancelUpload()
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
    dialogVisible.value = true
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
      dialogVisible.value = false
      fetchDatasets()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || 'Failed to update description')
    } finally {
      submitting.value = false
    }
  }
  
  const handleClose = (done) => {
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
    if (!text) return ''
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
  }
  
  .upload-card {
    margin-bottom: 20px;
    max-width: 800px;
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .el-upload__text em {
    color: #409EFF;
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
  
  .el-button--small {
    padding: 6px 12px;
  }
  
  .search-input {
    width: 200px;
    margin-right: 10px;
  }
  
  .el-button--primary {
    background-color: #409EFF;
    border-color: #409EFF;
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
  </style>