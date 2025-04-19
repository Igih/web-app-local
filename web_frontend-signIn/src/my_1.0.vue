<template>
    <el-container class="app-container">
      <el-header>
        <h1>Dataset Manager</h1>
      </el-header>
      
      <el-main>
        <!-- Upload section remains unchanged -->
        <el-card class="upload-card">
          <template #header>
            <div class="card-header">
              <span>Upload Dataset</span>
            </div>
          </template>
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
        </el-card>
  
        <!-- Dataset list with edit dialog -->
        <el-card class="dataset-card">
          <template #header>
            <div class="card-header">
              <span>Datasets</span>
              <el-button type="primary" @click="fetchDatasets" :loading="loading">
                Refresh
              </el-button>
            </div>
          </template>
  
          <el-table 
            v-loading="loading"
            :data="datasets"
            style="width: 100%"
          >
            <el-table-column prop="filename" label="File Name" />
            <el-table-column label="Size" width="120">
              <template #default="scope">
                {{ formatSize(scope.row.size) }}
              </template>
            </el-table-column>
            <!-- Description column with Edit button -->
            <el-table-column label="Description" width="300">
              <template #default="scope">
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="showEditDialog(scope.row)"
                >
                  Edit
                </el-button>
              </template>
            </el-table-column>
            <!-- Operations column with Download and Delete -->
            <el-table-column label="Operations" width="200">
              <template #default="scope">
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="downloadFile(scope.row.filename)"
                >
                  Download
                </el-button>
                <el-button 
                  type="danger" 
                  size="small" 
                  @click="deleteFile(scope.row.filename)"
                >
                  Delete
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
  
        <!-- Edit description dialog -->
        <el-dialog
          title="Edit Description"
          v-model="dialogVisible"
          width="30%"
          :before-close="handleClose"
        >
          <el-input
            v-model="currentDescription"
            type="textarea"
            :rows="4"
            placeholder="Enter description"
          />
          <template #footer>
            <span class="dialog-footer">
              <el-button @click="dialogVisible = false">Cancel</el-button>
              <el-button type="primary" @click="submitDescription">
                Submit
              </el-button>
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
  
  const datasets = ref([])
  const loading = ref(false)
  const dialogVisible = ref(false)
  const currentDescription = ref('')
  const currentFilename = ref('')
  
  const fetchDatasets = async () => {
    try {
      loading.value = true
      const response = await axios.get('/api/datasets')
      datasets.value = response.data.datasets
    } catch (error) {
      ElMessage.error('Failed to fetch datasets')
    } finally {
      loading.value = false
    }
  }
  
  const handleUpload = async (options) => {
    const formData = new FormData()
    formData.append('file', options.file)
    
    try {
      loading.value = true
      await axios.post('/api/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      ElMessage.success('Upload successful')
      fetchDatasets()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || 'Upload failed')
    } finally {
      loading.value = false
    }
  }
  
  const downloadFile = (filename) => {
    window.location.href = `/api/download/${filename}`
  }
  
  const deleteFile = async (filename) => {
    try {
      await ElMessageBox.confirm(
        `Are you sure you want to delete ${filename}?`,
        'Warning',
        {
          confirmButtonText: 'Delete',
          cancelButtonText: 'Cancel',
          type: 'warning'
        }
      )
      loading.value = true
      await axios.delete(`/api/datasets/${filename}`)
      ElMessage.success('File deleted successfully')
      fetchDatasets()
    } catch (error) {
      if (error !== 'cancel') {
        ElMessage.error(error.response?.data?.detail || 'Failed to delete file')
      }
    } finally {
      loading.value = false
    }
  }
  
  const showEditDialog = (row) => {
    currentFilename.value = row.filename
    currentDescription.value = row.description || ''
    dialogVisible.value = true
  }
  
  const submitDescription = async () => {
    try {
      await axios.put(`/api/datasets/${currentFilename.value}`, { 
        description: currentDescription.value 
      })
      ElMessage.success('Description updated')
      dialogVisible.value = false
      fetchDatasets()
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || 'Failed to update description')
    }
  }
  
  const handleClose = (done) => {
    ElMessageBox.confirm('Are you sure to close without saving?')
      .then(() => {
        done()
      })
      .catch(() => {})
  }
  
  const formatSize = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }
  
  onMounted(() => {
    fetchDatasets()
  })
  </script>
  
  <style scoped>
  .app-container {
    height: 100vh;
    padding: 20px;
  }
  
  .upload-card {
    margin-bottom: 20px;
    max-width: 500px;
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
    gap: 10px; /* 添加按钮之间的间距 */
  }
  
  .el-button--small {
    padding: 6px 12px;
  }
  </style>