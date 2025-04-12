<template>
  <el-container class="app-container">
    <!-- 添加切换按钮 -->
    <el-header class="sub-header">
      <div class="header-buttons">
        <el-button 
          :type="activeTab === 'adjustments' ? 'primary' : 'info'"
          @click="switchToAdjustments"
        >
          Data Adjustment
        </el-button>
        <el-button 
          :type="activeTab === 'categories' ? 'primary' : 'info'" 
          @click="switchToCategories"
        >
          Category Description
        </el-button>
      </div>
    </el-header>
    
    <el-main>
      <!-- Categories Tab (categories_show table) -->
      <div v-if="activeTab === 'categories'">
        <!-- New Upload Section for categories_show -->
        <el-card class="upload-card">
          <template #header>
            <div class="card-header">
              <span>Upload New Category Data</span>
            </div>
          </template>
          <el-form :model="newCategory" label-position="top" :rules="rules" ref="categoryForm">
            <el-form-item label="Sample Images (Exactly 1~6 required)">
              <el-upload
                :file-list="newCategory.images"
                :http-request="handleNewImageUpload"
                accept="image/*"
                :multiple="true"
                :limit="6"
                :on-exceed="handleExceed"
                list-type="picture"
                :on-remove="handleImageRemove"
                :before-upload="beforeImageUpload"
                :show-file-list="false"
              >
                <el-button type="primary">Click to upload</el-button>
                <template #tip>
                  <div class="el-upload__tip">
                    Upload up to 6 images
                  </div>
                </template>
              </el-upload>
            </el-form-item>
            <el-form-item label="Uploaded Images">
              <div v-if="newCategory.images.length > 0" class="uploaded-images">
                <div v-for="(image, index) in newCategory.images" :key="index" class="image-preview">
                  <img :src="getImagePreview(image.file)" alt="Preview" class="preview-image">
                  <span class="image-name">{{ image.name }}</span>
                  <el-button 
                    type="danger" 
                    size="small" 
                    @click="handleImageRemove(image, newCategory.images)"
                    class="remove-btn"
                  >
                    Remove
                  </el-button>
                </div>
              </div>
              <div v-else class="no-images">No images uploaded yet</div>
            </el-form-item>
            <el-form-item label="Description">
              <el-input v-model="newCategory.description" type="textarea" :rows="4" />
            </el-form-item>
            <el-form-item label="Category" prop="category" required>
              <el-input 
                v-model="newCategory.category" 
                type="textarea" 
                :rows="4" 
                :maxlength="6" 
                show-word-limit 
              />
            </el-form-item>
            <el-form-item label="Category Count" prop="count" required>
              <el-input 
                v-model.number="newCategory.count"
                type="number"
                placeholder="Enter category count"
                :min="0"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="submitNewCategory" :loading="submitting">Submit</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- Categories Display -->
        <el-card class="dataset-card">
          <template #header>
            <div class="card-header">
              <span>Categories Show</span>
              <el-button type="primary" @click="fetchCategoriesShow" :loading="loading">
                Refresh
              </el-button>
            </div>
          </template>
          <el-table v-loading="loading" :data="categoriesShow" style="width: 100%">
            <el-table-column label="Category" width="300">
              <template #default="scope">
                <span :title="scope.row.category">{{ truncate(scope.row.category, 20) }}</span>
              </template>
            </el-table-column>
            <el-table-column label="Category Count" width="150">
              <template #default="scope">
                <div class="count-cell">
                  <span>{{ scope.row.count || 0 }}</span>
                  <el-button 
                    type="primary" 
                    size="small" 
                    @click="showCountDialog(scope.row)"
                  >
                    Edit
                  </el-button>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="Sample Images" width="300">
              <template #default="scope">
                <span v-if="scope.row.images && Array.isArray(scope.row.images)">
                  已上传{{ scope.row.images.length }}张
                </span>
                <span v-else-if="scope.row.images">
                  已上传1张
                </span>
                <span v-else>
                  未上传图片
                </span>
              </template>
            </el-table-column>
            <el-table-column label="Description" width="300">
              <template #default="scope">
                <div class="description-cell">
                  <span :title="scope.row.description">{{ truncate(scope.row.description, 20) }}</span>
                  <el-button 
                    type="primary" 
                    size="small" 
                    @click="showDescriptionDialog(scope.row)"
                  >
                    Edit
                  </el-button>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="Operations" width="100">
              <template #default="scope">
                <el-button type="danger" size="small" @click="deleteCategory(scope.row.id)">
                  Delete
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </div>

      <!-- Adjustments Tab -->
      <div v-if="activeTab === 'adjustments'">
        <el-card class="upload-card">
          <template #header>
            <div class="card-header">
              <span>Upload Dataset</span>
            </div>
          </template>
          <el-form :model="uploadForm" label-position="top">
            <el-form-item label="Category" required>
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
              <span>Datasets</span>
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
            <el-table-column label="Categories" width="300">
              <template #default="scope">
                <div class="description-cell">
                  <span :title="scope.row.categories">{{ truncate(scope.row.categories, 20) }}</span>
                  <el-button type="primary" size="small" @click="showCategoriesDialog(scope.row)">
                    Edit
                  </el-button>
                </div>
              </template>
            </el-table-column>
            <el-table-column label="Operations" width="200">
              <template #default="scope">
                <el-button type="danger" size="small" @click="deleteFile(scope.row.filename)">
                  Delete
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

      <!-- Edit Dialogs -->
      <el-dialog title="Edit Description" v-model="dialogVisible" width="30%" :before-close="handleClose">
        <el-input v-model="currentDescription" type="textarea" :rows="4" placeholder="Enter description" />
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="dialogVisible = false">Cancel</el-button>
            <el-button type="primary" @click="submitDescription" :loading="submitting">Submit</el-button>
          </span>
        </template>
      </el-dialog>

      <el-dialog title="Edit Categories" v-model="categoriesDialogVisible" width="30%" :before-close="handleCategoriesClose">
        <el-input v-model="currentCategory" type="textarea" :rows="4" :maxlength="50" show-word-limit placeholder="Enter categories" />
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="categoriesDialogVisible = false">Cancel</el-button>
            <el-button type="primary" @click="submitCategory" :loading="submitting">Submit</el-button>
          </span>
        </template>
      </el-dialog>

      <el-dialog 
        title="Edit Category Count" 
        v-model="countDialogVisible" 
        width="30%" 
        :before-close="handleCountClose"
      >
        <el-form :model="currentCountForm" :rules="countRules" ref="countForm">
          <el-form-item label="Category Count" prop="count">
            <el-input 
              v-model.number="currentCountForm.count"
              type="number"
              placeholder="Enter category count"
              :min="0"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="countDialogVisible = false">Cancel</el-button>
            <el-button 
              type="primary" 
              @click="submitCount" 
              :loading="submitting"
            >
              Submit
            </el-button>
          </span>
        </template>
      </el-dialog>

      <el-dialog 
        title="Edit Description" 
        v-model="descriptionDialogVisible" 
        width="30%" 
        :before-close="handleDescriptionClose"
      >
        <el-form :model="currentDescriptionForm" ref="descriptionForm">
          <el-form-item label="Description">
            <el-input 
              v-model="currentDescriptionForm.description"
              type="textarea"
              :rows="4"
              placeholder="Enter description"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <span class="dialog-footer">
            <el-button @click="descriptionDialogVisible = false">Cancel</el-button>
            <el-button 
              type="primary" 
              @click="submitDescriptionUpdate" 
              :loading="submitting"
            >
              Submit
            </el-button>
          </span>
        </template>
      </el-dialog>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted} from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useUploadStore } from '@/stores/upload'

const authStore = useAuthStore()
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const datasets = ref([])
const categoriesShow = ref([])
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const categoriesDialogVisible = ref(false)
const currentDescription = ref('')
const currentCategory = ref('')
const currentRow = ref(null)
const activeTab = ref('adjustments')
const newCategory = ref({
  images: [],
  description: '',
  category: '',
  count: null
})
const categoryForm = ref(null)
const searchQuery = ref('')
const countDialogVisible = ref(false)
const currentCountForm = ref({ count: null })
const countForm = ref(null)
const descriptionDialogVisible = ref(false)
const currentDescriptionForm = ref({ description: '' })

const uploadStore = useUploadStore()
const uploadForm = ref({
  category: '',
  description: ''
})

const rules = {
  category: [
    { required: true, message: 'Category is required', trigger: 'blur' },
    { max: 6, message: 'Category must not exceed 6 characters', trigger: 'blur' }
  ],
  count: [
    { required: true, message: 'Category count is required', trigger: 'blur' },
    { type: 'number', message: 'Count must be a number', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (value !== null && !Number.isInteger(value)) {
          callback(new Error('Count must be an integer'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ]
}

const countRules = {
  count: [
    { required: true, message: 'Count is required', trigger: 'blur' },
    { type: 'number', message: 'Count must be a number', trigger: 'blur' },
    { 
      validator: (rule, value, callback) => {
        if (value !== null && !Number.isInteger(value)) {
          callback(new Error('Count must be an integer'))
        } else {
          callback()
        }
      }, 
      trigger: 'blur' 
    }
  ]
}

const fetchDatasets = async () => {
  try {
    loading.value = true
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      uploader_type: 'admin' // 添加此参数以只获取Admin数据
    }
    if (searchQuery.value) {
      params.filename_filter = searchQuery.value
    }
    const response = await axios.get('/api/datasets', { params })
    datasets.value = response.data.datasets
    total.value = response.data.total
  } catch (error) {
    ElMessage.error('Failed to fetch datasets: ' + (error.message || 'Unknown error'))
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

const fetchCategoriesShow = async () => {
  try {
    loading.value = true
    const response = await axios.get('/api/categories_show')
    categoriesShow.value = response.data.categories_show.map(item => {
      return {
        ...item,
        images: Array.isArray(item.images) ? item.images : []
      }
    })
  } catch (error) {
    ElMessage.error('Failed to fetch categories show: ' + (error.message || 'Unknown error'))
  } finally {
    loading.value = false
  }
}

const handleUpload = async (options) => {
  const file = options.file
  const formData = new FormData()
  formData.append('file', file)
  formData.append('category', uploadForm.value.category)
  formData.append('description', uploadForm.value.description || '')

  if (!authStore.token) {
    ElMessage.error('Please login to upload datasets')
    return
  }

  if (!uploadForm.value.category) {
    ElMessage.error('Category is required')
    return
  }

  try {
    uploadStore.startUpload()

    const config = {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': `Bearer ${authStore.token}`
      },
      signal: uploadStore.controller.signal,
      onUploadProgress: (progressEvent) => {
        const { loaded, total } = progressEvent
        uploadStore.updateProgress(loaded, total)
      }
    }

    await axios.post('/api/upload', formData, config)
    ElMessage.success('Upload successful')
    uploadForm.value.category = '' // 清空表单
    uploadForm.value.description = ''
    fetchDatasets()
  } catch (error) {
    if (error.name === 'AbortError') {
      ElMessage.info('Upload canceled')
    } else if (error.response?.status === 401) {
      ElMessage.error('Session expired, please login again')
      authStore.logout()
      window.location.href = '/'
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

const beforeImageUpload = (file) => {
  return true
}

const handleNewImageUpload = async (options) => {
  try {
    await beforeImageUpload(options.file)
    newCategory.value.images.push({ name: options.file.name, file: options.file })
  } catch (error) {
    console.error('Image upload rejected:', error.message)
  }
}

const getImagePreview = (file) => {
  return URL.createObjectURL(file)
}

const handleImageRemove = (file, fileList) => {
  const index = fileList.findIndex(f => f.uid === file.uid || f.name === file.name)
  if (index !== -1) {
    fileList.splice(index, 1)
  }
}

const handleExceed = () => {
  ElMessage.warning('You can only upload 6 images')
}

const submitNewCategory = async () => {
  try {
    await categoryForm.value.validate()
  } catch (error) {
    ElMessage.error('Please fix the form errors before submitting')
    return
  }

  if (newCategory.value.images.length === 0 || newCategory.value.images.length > 6) {
    ElMessage.error('Please upload between 1 and 6 images')
    return
  }
  if (!newCategory.value.category) {
    ElMessage.error('Category is required')
    return
  }
  if (newCategory.value.category.length > 6) {
    ElMessage.error('Category must not exceed 6 characters')
    return
  }
  if (newCategory.value.count === null || 
      isNaN(newCategory.value.count) || 
      !Number.isInteger(newCategory.value.count)) {
    ElMessage.error('Category count must be an integer')
    return
  }

  if (!authStore.token) {
    ElMessage.error('Please login to add categories')
    return
  }

  const formData = new FormData()
  newCategory.value.images.forEach((image) => {
    formData.append('images', image.file)
  })
  formData.append('description', newCategory.value.description)
  formData.append('category', newCategory.value.category.toLowerCase())
  formData.append('count', newCategory.value.count)

  try {
    submitting.value = true
    await axios.post('/api/categories_show', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
        'Authorization': `Bearer ${authStore.token}` // 添加 Authorization 头
      }
    })
    ElMessage.success('Category added successfully')
    newCategory.value = { images: [], description: '', category: '', count: null }
    fetchCategoriesShow()
  } catch (error) {
    if (error.response?.status === 401) {
      ElMessage.error('Session expired, please login again')
      authStore.logout()
      window.location.href = '/'
    } else if (error.response?.status === 403) {
      ElMessage.error('Admin privileges required to add categories')
    } else {
      const errorMsg = error.response?.data?.detail || 'Failed to add category: ' + error.message
      ElMessage.error(errorMsg)
    }
  } finally {
    submitting.value = false
  }
}

const showCountDialog = (row) => {
  currentRow.value = row
  currentCountForm.value.count = row.count
  countDialogVisible.value = true
}

const handleCountClose = (done) => {
  ElMessageBox.confirm('Are you sure to close without saving?')
    .then(() => done())
    .catch(() => {})
}

const submitCount = async () => {
  try {
    await countForm.value.validate()
    const countValue = Number(currentCountForm.value.count)
    if (!Number.isInteger(countValue)) {
      ElMessage.error('Count must be an integer')
      return
    }
    submitting.value = true
    
    await axios.put(`/api/categories_show/${currentRow.value.id}`, {
      count: countValue
    }, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    
    ElMessage.success('Count updated')
    countDialogVisible.value = false
    fetchCategoriesShow()
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to update count'
    ElMessage.error(errorMsg)
  } finally {
    submitting.value = false
  }
}

const showDescriptionDialog = (row) => {
  currentRow.value = row
  currentDescriptionForm.value.description = row.description || ''
  descriptionDialogVisible.value = true
}

const handleDescriptionClose = (done) => {
  ElMessageBox.confirm('Are you sure to close without saving?')
    .then(() => done())
    .catch(() => {})
}

const submitDescriptionUpdate = async () => {
  try {
    submitting.value = true
    await axios.put(`/api/categories_show/${currentRow.value.id}`, {
      description: currentDescriptionForm.value.description
    }, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    
    ElMessage.success('Description updated')
    descriptionDialogVisible.value = false
    fetchCategoriesShow()
  } catch (error) {
    const errorMsg = error.response?.data?.detail || error.message || 'Failed to update description'
    ElMessage.error(errorMsg)
  } finally {
    submitting.value = false
  }
}

const deleteCategory = async (id) => {
  try {
    await ElMessageBox.confirm('Are you sure you want to delete this category?', 'Warning', {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning'
    })
    loading.value = true
    await axios.delete(`/api/categories_show/${id}`)
    ElMessage.success('Category deleted successfully')
    fetchCategoriesShow()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || 'Failed to delete category')
    }
  } finally {
    loading.value = false
  }
}

const deleteFile = async (filename) => {
  try {
    await ElMessageBox.confirm(`Are you sure you want to delete ${filename}?`, 'Warning', {
      confirmButtonText: 'Delete',
      cancelButtonText: 'Cancel',
      type: 'warning'
    })
    loading.value = true
    await axios.delete(`/api/datasets/${filename}`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    ElMessage.success('File and associated text file deleted successfully')
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
  currentRow.value = row
  currentDescription.value = row.description || ''
  dialogVisible.value = true
}

const showCategoriesDialog = (row) => {
  currentRow.value = row
  currentCategory.value = row.categories || ''
  categoriesDialogVisible.value = true
}

const submitDescription = async () => {
  try {
    submitting.value = true
    const endpoint = activeTab.value === 'categories' 
      ? `/api/categories_show/${currentRow.value.id}` 
      : `/api/datasets/${currentRow.value.filename}`
    await axios.put(endpoint, { description: currentDescription.value }, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    ElMessage.success('Description updated and saved to file')
    dialogVisible.value = false
    activeTab.value === 'categories' ? fetchCategoriesShow() : fetchDatasets()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to update description')
  } finally {
    submitting.value = false
  }
}

const submitCategory = async () => {
  try {
    submitting.value = true
    const endpoint = activeTab.value === 'categories' ? `/api/categories_show/${currentRow.value.id}` : `/api/datasets/${currentRow.value.filename}`
    const payload = activeTab.value === 'categories' ? 
      { category: currentCategory.value } : 
      { categories: currentCategory.value }
    await axios.put(endpoint, payload)
    ElMessage.success(activeTab.value === 'categories' ? 'Category updated' : 'Categories updated')
    categoriesDialogVisible.value = false
    activeTab.value === 'categories' ? fetchCategoriesShow() : fetchDatasets()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to update ' + (activeTab.value === 'categories' ? 'category' : 'categories'))
  } finally {
    submitting.value = false
  }
}

const handleClose = (done) => {
  ElMessageBox.confirm('Are you sure to close without saving?')
    .then(() => done())
    .catch(() => {})
}

const handleCategoriesClose = (done) => {
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

const switchToCategories = () => {
  activeTab.value = 'categories'
  fetchCategoriesShow()
}

const switchToAdjustments = () => {
  activeTab.value = 'adjustments'
  fetchDatasets()
}

// 组件卸载时清理
onUnmounted(() => {
  
})
</script>

<style scoped>
.app-container { 
  padding: 20px;
  margin-top: 0;
}

.sub-header {
  height: auto !important;
  padding: 10px 20px;
  background-color: #f5f7fa;
  border-bottom: 1px solid #e6e6e6;
}

.header-buttons {
  display: flex;
  gap: 10px;
  justify-content: center;
  width: 100%;
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

.uploaded-images {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
}

.image-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  border: 1px solid #eee;
  padding: 5px;
  border-radius: 4px;
}

.preview-image {
  width: 100px;
  height: 80px;
  object-fit: contain;
}

.image-name {
  font-size: 12px;
  margin: 5px 0;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remove-btn {
  margin-top: 5px;
}

.no-images {
  color: #999;
  font-style: italic;
}

.search-input {
  width: 200px;
  margin-right: 10px;
}

.el-button--info {
  background-color: #909399;
  border-color: #909399;
  color: #fff;
}

.el-button--primary {
  background-color: #409EFF;
  border-color: #409EFF;
  color: #fff;
}

.el-button--info:hover {
  background-color: #a6a9ad;
  border-color: #a6a9ad;
}

.el-button--primary:hover {
  background-color: #66b1ff;
  border-color: #66b1ff;
}

.count-cell {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0 10px;
}

.count-cell span {
  flex-grow: 1;
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