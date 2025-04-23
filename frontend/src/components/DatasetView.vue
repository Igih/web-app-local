<template>
  <div class="plane-dataset-container">
    <div class="dataset-section">
      <h1>
        <Icon :icon="categoryIcon" class="category-icon" />
        {{ formattedCategory }} Datasets
      </h1>
      <p v-if="categoryDescription">{{ categoryDescription }}</p>
    </div>

    <div class="sample-images" v-if="sampleImages.length > 0">
      <h2>Sample Images</h2>
      <div class="image-grid">
        <img
          v-for="(image, index) in sampleImages"
          :key="index"
          :src="getImageUrl(image)"
          :alt="`Sample ${formattedCategory} ${index + 1}`"
          @error="handleImageError"
        />
      </div>
    </div>

    <div class="download-list">
      <h2>Available Datasets for Download</h2>

      <!-- Moved search-container here -->
      <div class="search-container">
        <el-input
          v-model="searchQuery"
          placeholder="Search by filename..."
          clearable
          @keyup.enter="searchDatasets"
          class="search-input search-input-filename"
        />
        <el-select
          v-model="uploaderType"
          placeholder="Uploader Type"
          class="search-input search-input-uploader"
          @change="searchDatasets"
        >
          <el-option label="All" value="all" />
          <el-option label="Admin" value="admin" />
          <el-option label="User" value="user" />
        </el-select>
        <el-autocomplete
          v-model="usernameQuery"
          :fetch-suggestions="queryUsernames"
          placeholder="Search by username"
          clearable
          :disabled="uploaderType !== 'user'"
          @select="searchDatasets"
          class="search-input search-input-username"
        />
        <el-button type="primary" @click="searchDatasets" class="search-button">
          Search
        </el-button>
      </div>

      <div v-if="loading" class="loading">Loading datasets...</div>
      <div v-else-if="datasets.length === 0" class="no-data">No datasets available</div>
      <div v-else class="download-items">
        <div class="download-items-header">
          <el-button
            v-if="selectedDatasets.length > 0"
            type="success"
            @click="exportSelectedPaths"
            class="export-button"
          >
            Export File Paths
          </el-button>
          <el-button
            v-if="selectedDatasets.length > 0"
            type="warning"
            @click="selectedDatasets = []"
            class="clear-button"
          >
            Clear Selections
          </el-button>
        </div>

        <div v-for="dataset in datasets" :key="dataset.id" class="download-item">
          <div class="dataset-header">
            <el-checkbox
              v-model="selectedDatasets"
              :value="dataset.id"
            />
            <h3>{{ dataset.filename }}</h3>
          </div>
          <div class="description-container">
            <p
              :class="{ 'description-collapsed': !expandedDescriptions[dataset.id] }"
              ref="descriptionText"
            >
              {{ dataset.description || 'No description available' }}
            </p>
            <el-button
              v-if="isDescriptionLong(dataset.id)"
              type="text"
              @click="toggleDescription(dataset.id)"
              class="more-button"
            >
              {{ expandedDescriptions[dataset.id] ? 'Less' : 'More' }}
            </el-button>
          </div>
          <p><strong>Category:</strong> {{ dataset.category || 'Not specified' }}</p>
          <p><strong>Size:</strong> {{ formatSize(dataset.size) }}</p>
          <p><strong>Uploader:</strong> {{ dataset.uploader_type === 'admin' ? 'Admin' : dataset.uploader_name }}</p>
          <p><strong>Upload Date:</strong> {{ formatDate(dataset.upload_date) }}</p>
          <el-button
            type="primary"
            @click="currentUser ? downloadDataset(dataset.id) : showLoginPrompt()"
            class="download-button"
          >
            Download
          </el-button>
        </div>
      </div>

      <el-pagination
        v-if="total > 0"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[5, 10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
        class="pagination"
      />
    </div>

    <el-button
      v-if="showBackToTop"
      class="back-to-top"
      type="primary"
      circle
      @click="scrollToTop"
    >
      <Icon icon="mdi:arrow-up" class="top-icon" />
    </el-button>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import { Icon } from '@iconify/vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import fallbackImage from '@/assets/00214.jpg'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const category = ref(route.params.category)
const datasets = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const categoryDescription = ref('')
const loading = ref(false)
const sampleImages = ref([])
const expandedDescriptions = ref([])
const selectedDatasets = ref([]) // Stores dataset IDs across all pages
const selectedDatasetPaths = ref([]) // Stores paths of selected datasets
const searchQuery = ref('')
const uploaderType = ref('all')
const usernameQuery = ref('')
const showBackToTop = ref(false)

const currentUser = computed(() => authStore.currentUser)

const formattedCategory = computed(() => {
  return category.value.charAt(0).toUpperCase() + category.value.slice(1)
})

const categoryIcon = computed(() => {
  return getCategoryIcon(category.value)
})

const getImageUrl = (filename) => {
  if (filename.startsWith('/category_images/')) {
    return filename
  }
  return `/category_images/${filename}`
}

const handleImageError = (event) => {
  event.target.src = fallbackImage
}

const scrollToTop = () => {
  window.scrollTo({
    top: 0,
    behavior: 'smooth',
  })
}

const handleScroll = () => {
  showBackToTop.value = window.scrollY > 300
}

const isDescriptionLong = (datasetId) => {
  const dataset = datasets.value.find((d) => d.id === datasetId)
  if (!dataset || !dataset.description) return false
  return dataset.description.length > 100
}

const toggleDescription = (datasetId) => {
  expandedDescriptions.value[datasetId] = !expandedDescriptions.value[datasetId]
}

// Watch selectedDatasets to update selectedDatasetPaths
watch(selectedDatasets, (newSelection) => {
  // Map selected dataset IDs to their paths
  selectedDatasetPaths.value = datasets.value
    .filter((dataset) => newSelection.includes(dataset.id))
    .map((dataset) => dataset.path)
    .filter((path) => path) // Ensure no undefined paths
})

const exportSelectedPaths = async () => {
  if (!currentUser.value) {
    showLoginPrompt()
    return
  }
  if (selectedDatasets.value.length === 0) {
    ElMessage.warning('Please select at least one dataset to export')
    return
  }
  try {
    // Fetch paths for all selected dataset IDs
    const response = await axios.post(
      '/api/datasets/paths',
      selectedDatasets.value,
      {
        headers: { Authorization: `Bearer ${authStore.token}` },
      }
    )
    const paths = response.data.paths
    if (paths.length === 0) {
      ElMessage.warning('No valid paths found for selected datasets')
      return
    }
    // Export paths to a text file
    const content = paths.join('\n')
    const blob = new Blob([content], { type: 'text/plain' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `dataset_paths_${new Date().toISOString().slice(0, 10)}.txt`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('File paths exported successfully')
  } catch (error) {
    ElMessage.error('Failed to export file paths: ' + (error.response?.data?.detail || error.message))
  }
}

const queryUsernames = async (queryString, cb) => {
  if (!queryString) {
    cb([])
    return
  }
  try {
    const response = await axios.get('/api/users/search', {
      params: { query: queryString },
      headers: { Authorization: `Bearer ${authStore.token}` },
    })
    const results = response.data.map((user) => ({
      value: user.username,
      id: user.id,
    }))
    cb(results)
  } catch (error) {
    ElMessage.error('Failed to search usernames')
    cb([])
  }
}

const fetchDatasets = async () => {
  loading.value = true
  try {
    const params = {
      category_filter: category.value,
      page: currentPage.value,
      page_size: pageSize.value,
    }
    if (searchQuery.value) {
      params.filename_filter = searchQuery.value
    }
    if (uploaderType.value) {
      params.uploader_type = uploaderType.value
    }
    if (usernameQuery.value && uploaderType.value === 'user') {
      params.username_filter = usernameQuery.value
    }

    const [datasetsRes, categoryRes] = await Promise.all([
      axios.get('/api/datasets', { params }),
      axios.get('/api/categories_show', {
        params: { category: category.value },
      }),
    ])

    datasets.value = datasetsRes.data.datasets
    total.value = datasetsRes.data.total

    expandedDescriptions.value = []
    datasets.value.forEach((dataset) => {
      expandedDescriptions.value[dataset.id] = false
    })

    const matchingCategory = categoryRes.data.categories_show.find(
      (cat) => cat.category.toLowerCase() === category.value.toLowerCase()
    )
    if (matchingCategory) {
      categoryDescription.value = matchingCategory.description
      sampleImages.value = matchingCategory.images || []
    } else {
      categoryDescription.value = ''
      sampleImages.value = []
    }

    // Update selectedDatasetPaths based on current selections
    selectedDatasetPaths.value = datasets.value
      .filter((dataset) => selectedDatasets.value.includes(dataset.id))
      .map((dataset) => dataset.path)
      .filter((path) => path)
  } catch (error) {
    ElMessage.error(
      'Failed to fetch datasets: ' +
        (error.response?.data?.detail || error.message)
    )
  } finally {
    loading.value = false
  }
}

const searchDatasets = () => {
  currentPage.value = 1
  selectedDatasets.value = [] // Clear selections on new search
  fetchDatasets()
}

const getCategoryIcon = (category) => {
  const iconMap = {
    plane: 'mdi:airplane',
    car: 'mdi:car',
    ship: 'mdi:ferry',
    tank: 'mdi:tank',
    drone: 'mdi:drone',
  }
  return iconMap[category.toLowerCase()] || 'mdi:database'
}

const formatSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

const formatDate = (date) => {
  return new Date(date).toLocaleString()
}

const showLoginPrompt = () => {
  ElMessage({
    message: 'Please login to download datasets',
    type: 'warning',
    duration: 3000,
  })
  router.push('/')
}

const downloadDataset = (datasetId) => {
  if (!currentUser.value) {
    showLoginPrompt()
    return
  }
  window.location.href = `/api/download/${datasetId}`
}

const handleSizeChange = (newSize) => {
  pageSize.value = newSize
  currentPage.value = 1
  fetchDatasets()
}

const handlePageChange = (newPage) => {
  currentPage.value = newPage
  fetchDatasets()
}

watch(
  () => route.params.category,
  (newCategory) => {
    category.value = newCategory
    currentPage.value = 1
    selectedDatasets.value = []
    selectedDatasetPaths.value = []
    fetchDatasets()
  },
  { immediate: true }
)

onMounted(() => {
  fetchDatasets()
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
.plane-dataset-container {
  min-height: 100vh;
  background-color: #f5f7fa;
  font-family: 'Arial', sans-serif;
}

.dataset-section {
  text-align: center;
  padding: 50px 20px;
  overflow: visible;
  height: auto;
}

.dataset-section h1 {
  font-size: 48px;
  font-weight: bold;
  color: #1f2a44;
  margin-bottom: 20px;
  display: block;
  visibility: visible;
  opacity: 1;
  white-space: normal;
  word-break: normal;
}

.dataset-section p {
  text-align: justify;
  margin: 10px auto;
  line-height: 1.6;
  font-size: 20px;
  color: #606266;
  max-width: 1100px;
  padding: 0 20px;
}

.sample-images {
  padding: 50px 20px;
  text-align: center;
}

.sample-images h2 {
  font-size: 32px;
  color: #1f2a44;
  margin-bottom: 30px;
}

.image-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.image-grid img {
  width: 300px;
  height: 200px;
  object-fit: cover;
  border-radius: 10px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.download-list {
  padding: 50px 20px;
  text-align: center;
}

.download-list h2 {
  font-size: 32px;
  color: #1f2a44;
  margin-bottom: 20px; /* Reduced margin to bring search closer */
}

.download-items {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  position: relative;
}

.download-item {
  background-color: #fff;
  padding: 20px;
  border-radius: 10px;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  width: 70vw;
  max-width: none;
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.download-item h3 {
  font-size: 24px;
  color: #1f2a44;
  margin-bottom: 10px;
  word-break: break-word;
}

.download-item p {
  font-size: 16px;
  color: #606266;
  margin-bottom: 10px;
  word-break: break-word;
}

.loading {
  font-size: 18px;
  color: #606266;
}

.no-data {
  font-size: 18px;
  color: #909399;
}

.pagination {
  margin-top: 30px;
  display: flex;
  justify-content: center;
}

.back-to-top {
  position: fixed;
  bottom: 50px;
  right: 50px;
  z-index: 1000;
  width: 50px;
  height: 50px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  transition: opacity 0.3s ease;
}

.back-to-top:hover {
  opacity: 0.8;
}

.top-icon {
  font-size: 24px;
}

.description-container {
  position: relative;
  margin-bottom: 10px;
  width: 100%;
}

.description-collapsed {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  line-clamp: 2;
  overflow: hidden;
  text-overflow: ellipsis;
  max-height: 3em;
  line-height: 1.5em;
}

.more-button {
  padding: 0;
  margin-left: 10px;
  color: #409EFF;
  font-size: 14px;
  text-transform: uppercase;
}

.more-button:hover {
  color: #66b1ff;
}

.download-button {
  width: auto;
  padding: 8px 20px;
  align-self: flex-start;
}

.download-items-header {
  width: 70vw;
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.search-container {
  width: 660px; /* Adjusted to accommodate new widths */
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 auto 30px; /* Center and add spacing below */
}

/* Specific widths for each input */
.search-input-filename {
  width: 300px; /* Increased width for filename search */
}

.search-input-uploader {
  width: 200px; /* Kept the same for uploader type */
}

.search-input-username {
  width: 150px; /* Decreased width for username search */
}

.search-button {
  padding: 8px 20px;
}

.export-button {
  padding: 8px 20px;
  width: auto;
}

.dataset-header {
  display: flex;
  align-items: center;
  gap: 10px; /* 控制复选框和文件名之间的间距 */
  margin-bottom: 10px;
  width: 100%;
}

.dataset-header h3 {
  margin: 0;
  flex-grow: 1;
}
</style>