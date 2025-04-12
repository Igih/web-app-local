<template>
  <div class="plane-dataset-container">
    <!-- 数据集标题和描述 -->
    <div class="dataset-section">
      <h1>
        <Icon :icon="categoryIcon" class="category-icon" />
        {{ formattedCategory }} Datasets
      </h1>
      <p v-if="categoryDescription">{{ categoryDescription }}</p>
    </div>

    <!-- 样本图片 -->
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

    <!-- 数据集列表 -->
    <div class="download-list">
      <h2>Available Datasets for Download</h2>
      
      <div v-if="loading" class="loading">Loading datasets...</div>
      <div v-else-if="datasets.length === 0" class="no-data">No datasets available</div>
      <div v-else class="download-items">
        <div class="search-container">
          <el-input
            v-model="searchQuery"
            placeholder="Search by filename..."
            clearable
            @keyup.enter="searchDatasets"
            class="search-input"
          />
          <el-button type="primary" @click="searchDatasets" class="search-button">
            Search
          </el-button>
        </div>

        <div class="download-items-header">
          <el-button 
            v-if="selectedDatasets.length > 0"
            type="success" 
            @click="exportSelectedPaths"
            class="export-button"
          >
            Export File Paths
          </el-button>
        </div>

        <div v-for="dataset in datasets" :key="dataset.filename" class="download-item">
          <div class="dataset-header">
            <el-checkbox 
              v-model="selectedDatasets" 
              :label="dataset.filename"
              @change="handleCheckboxChange"
            />
            <h3>{{ dataset.filename }}</h3>
          </div>

          <div class="description-container">
            <p 
              :class="{ 'description-collapsed': !expandedDescriptions[dataset.filename] }"
              ref="descriptionText"
            >
              {{ dataset.description || 'No description available' }}
            </p>
            <el-button 
              v-if="isDescriptionLong(dataset.filename)"
              type="text" 
              @click="toggleDescription(dataset.filename)"
              class="more-button"
            >
              {{ expandedDescriptions[dataset.filename] ? 'Less' : 'More' }}
            </el-button>
          </div>
          <p><strong>Categories:</strong> {{ dataset.categories || 'Not specified' }}</p>
          <p><strong>Size:</strong> {{ formatSize(dataset.size) }}</p>
          <el-button 
            type="primary" 
            @click="currentUser ? downloadDataset(dataset.filename) : showLoginPrompt()"
            class="download-button"
          >
            Download
          </el-button>
        </div>
      </div>
      
      <!-- 分页控制 -->
      <el-pagination
        v-if="total > 0"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
        class="pagination"
      />
    </div>

    <!-- 回到顶部按钮 -->
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

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const category = ref(route.params.category)
const datasets = ref([])
const currentPage = ref(1)
const pageSize = ref(10)
const total = ref(0)
const totalDatasets = ref(0)
const categoryDescription = ref('')
const loading = ref(false)
const sampleImages = ref([])
const expandedDescriptions = ref({})
const selectedDatasets = ref([])
const searchQuery = ref('')
const showBackToTop = ref(false)

const currentUser = computed(() => authStore.currentUser)

// 计算属性
const formattedCategory = computed(() => {
  return category.value.charAt(0).toUpperCase() + category.value.slice(1)
})

const categoryIcon = computed(() => {
  return getCategoryIcon(category.value)
})

// 获取完整的图片URL
const getImageUrl = (filename) => {
  return `/category_images/${filename}`
}

// 图片加载失败处理
const handleImageError = (event) => {
  event.target.src = '@/assets/00214.jpg'
}

// 滚动到顶部
const scrollToTop = () => {
  window.scrollTo({
    top: 0,
    behavior: 'smooth',
  })
}

// 监听滚动事件
const handleScroll = () => {
  showBackToTop.value = window.scrollY > 300
}

// 判断描述是否过长（例如超过100个字符）
const isDescriptionLong = (filename) => {
  const dataset = datasets.value.find(d => d.filename === filename)
  if (!dataset || !dataset.description) return false
  return dataset.description.length > 100
}

// 切换描述的展开/收起状态
const toggleDescription = (filename) => {
  expandedDescriptions.value[filename] = !expandedDescriptions.value[filename]
}

// 处理复选框变化
const handleCheckboxChange = () => {
  console.log('Selected datasets:', selectedDatasets.value)
}

// 导出选中的文件路径
const exportSelectedPaths = () => {
  if (selectedDatasets.value.length === 0) {
    ElMessage.warning('Please select at least one dataset to export')
    return
  }

  const content = selectedDatasets.value
    .map(filename => `/datasets/${filename}`)
    .join('\n')
  
  const blob = new Blob([content], { type: 'text/plain' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `dataset_paths_${new Date().toISOString().slice(0,10)}.txt`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
  
  ElMessage.success('File paths exported successfully')
}

// 获取数据集（支持搜索）
const fetchDatasets = async () => {
  loading.value = true
  try {
    const params = {
      category_filter: category.value,
      page: currentPage.value,
      page_size: pageSize.value
    }
    if (searchQuery.value) {
      params.filename_filter = searchQuery.value
    }

    const [datasetsRes, categoryRes] = await Promise.all([
      axios.get('/api/datasets', { params }),
      axios.get('/api/categories_show', {
        params: { category: category.value }
      })
    ])
    
    datasets.value = datasetsRes.data.datasets
    totalDatasets.value = datasetsRes.data.total
    total.value = datasetsRes.data.total
    
    expandedDescriptions.value = {}
    datasets.value.forEach(dataset => {
      expandedDescriptions.value[dataset.filename] = false
    })

    const matchingCategory = categoryRes.data.categories_show.find(
      cat => cat.category.toLowerCase() === category.value.toLowerCase()
    )
    if (matchingCategory) {
      categoryDescription.value = matchingCategory.description
      sampleImages.value = matchingCategory.images || []
    } else {
      categoryDescription.value = ''
      sampleImages.value = []
    }
  } catch (error) {
    console.error('Failed to fetch data:', error)
  } finally {
    loading.value = false
  }
}

// 搜索数据集
const searchDatasets = () => {
  currentPage.value = 1
  fetchDatasets()
}

// 图标映射
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

// 格式化文件大小
const formatSize = (bytes) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

// 显示登录提示
const showLoginPrompt = () => {
  ElMessage({
    message: 'Please login to download datasets',
    type: 'warning',
    duration: 3000
  })
  router.push('/') // 跳转到首页，登录对话框由 Layout.vue 处理
}

// 下载数据集
const downloadDataset = (filename) => {
  if (!currentUser.value) {
    showLoginPrompt()
    return
  }
  window.location.href = `/api/download/${filename}`
}

// 分页大小变化
const handleSizeChange = (newSize) => {
  pageSize.value = newSize
  currentPage.value = 1
  fetchDatasets()
}

// 分页页码变化
const handlePageChange = (newPage) => {
  currentPage.value = newPage
  fetchDatasets()
}

// 监听路由参数变化
watch(
  () => route.params.category,
  (newCategory) => {
    category.value = newCategory
    currentPage.value = 1
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

.image-grid img:only-child {
  flex: 0 0 auto;
}

.download-list {
  padding: 50px 20px;
  text-align: center;
}

.download-list h2 {
  font-size: 32px;
  color: #1f2a44;
  margin-bottom: 30px;
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
  display: box;
  -webkit-box-orient: vertical;
  box-orient: vertical;
  -webkit-line-clamp: 2;
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
  display: flex;
  align-items: center;
  gap: 10px;
}

.search-input {
  width: 300px;
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
  gap: 10px;
  margin-bottom: 10px;
  width: 100%;
}

.dataset-header h3 {
  margin: 0;
  flex-grow: 1;
}
</style>