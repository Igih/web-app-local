<template>
  <div class="plane-dataset-container">
    <el-header class="header">
      <div class="logo">EIP</div>
      <el-menu
        :default-active="activeIndex"
        class="nav-menu"
        mode="horizontal"
        @select="handleSelect"
      >
        <el-sub-menu index="1">
          <template #title>
            <svg class="menu-icon" aria-hidden="true">
              <use href="/icons/mdi.svg#database"></use>
            </svg>
            <span>Datasets</span>
          </template>
          <el-menu-item index="1-1" @click="goToPlaneDataset">
            <svg class="menu-icon" aria-hidden="true">
              <use href="/icons/mdi.svg#airplane"></use>
            </svg>
            <span>Plane</span>
          </el-menu-item>
          <el-menu-item index="1-2">
            <svg class="menu-icon" aria-hidden="true">
              <use href="/icons/mdi.svg#car"></use>
            </svg>
            <span>Car</span>
          </el-menu-item>
          <el-menu-item index="1-3">
            <svg class="menu-icon" aria-hidden="true">
              <use href="/icons/mdi.svg#ferry"></use>
            </svg>
            <span>Ship</span>
          </el-menu-item>
          <el-menu-item index="1-4">
            <svg class="menu-icon" aria-hidden="true">
              <use href="/icons/mdi.svg#tank"></use>
            </svg>
            <span>Tank</span>
          </el-menu-item>
        </el-sub-menu>
        <el-tooltip content="Innovative solutions for computer vision challenges." placement="bottom">
          <el-sub-menu index="2">
            <template #title>
              <svg class="menu-icon" aria-hidden="true">
                <use href="/icons/mdi.svg#lightbulb"></use>
              </svg>
              <span>Solutions</span>
            </template>
            <el-menu-item index="2-1">Solution 1</el-menu-item>
            <el-menu-item index="2-2">Solution 2</el-menu-item>
          </el-sub-menu>
        </el-tooltip>
        <el-tooltip content="Resources for learning and development." placement="bottom">
          <el-sub-menu index="3">
            <template #title>
              <svg class="menu-icon" aria-hidden="true">
                <use href="/icons/mdi.svg#book-open"></use>
              </svg>
              <span>Resource</span>
            </template>
            <el-menu-item index="3-1">
              <svg class="menu-icon" aria-hidden="true">
                <use href="/icons/mdi.svg#drone"></use>
              </svg>
              <span>Drone</span>
            </el-menu-item>
            <el-menu-item index="3-2">
              <svg class="menu-icon" aria-hidden="true">
                <use href="/icons/mdi.svg#map"></use>
              </svg>
              <span>Altlas</span>
            </el-menu-item>
          </el-sub-menu>
        </el-tooltip>
        <el-tooltip content="Explore our pricing plans for all budgets." placement="bottom">
          <el-menu-item index="4">
            <svg class="menu-icon" aria-hidden="true">
              <use href="/icons/mdi.svg#tag"></use>
            </svg>
            <span>Pricing</span>
          </el-menu-item>
        </el-tooltip>
        <el-tooltip content="Access detailed documentation for developers." placement="bottom">
          <el-menu-item index="5">
            <svg class="menu-icon" aria-hidden="true">
              <use href="/icons/mdi.svg#document"></use>
            </svg>
            <span>Docs</span>
          </el-menu-item>
        </el-tooltip>
        <el-tooltip content="Read the latest updates and insights on our blog." placement="bottom">
          <el-menu-item index="6">
            <svg class="menu-icon" aria-hidden="true">
              <use href="/icons/mdi.svg#newspaper"></use>
            </svg>
            <span>Blog</span>
          </el-menu-item>
        </el-tooltip>
      </el-menu>
      <div class="header-actions">
        <el-link class="sign-in" :underline="false">Sign In</el-link>
        <el-button class="demo-btn">Book a Demo</el-button>
        <el-button type="primary" class="start-btn">Get Started</el-button>
      </div>
    </el-header>

    <div class="dataset-section">
      <h1>Plane Dataset</h1>
      <p>
        The Plane Dataset contains over 10,000 annotated images of various aircraft, including commercial jets, military planes, and private aircraft. This dataset is ideal for training object detection and classification models for aviation-related computer vision applications.
      </p>
      <div class="dataset-actions">
        <el-button type="primary" @click="downloadDataset">Download Dataset</el-button>
        <el-button @click="exploreSamples">Explore Samples</el-button>
      </div>
    </div>

    <div class="sample-images">
      <h2>Sample Images</h2>
      <div class="image-grid">
        <img src="/icons/plane-sample-1.svg" alt="Plane 1" />
        <img src="/icons/plane-sample-2.svg" alt="Plane 2" />
        <img src="/icons/plane-sample-3.svg" alt="Plane 3" />
      </div>
    </div>

    <div class="download-list">
      <h2>Available Datasets for Download</h2>
      <div v-if="loading" class="loading">Loading datasets...</div>
      <div v-else-if="planeDatasets.length === 0" class="no-data">No plane datasets available</div>
      <div v-else class="download-items">
        <div v-for="dataset in planeDatasets" :key="dataset.filename" class="download-item">
          <h3>{{ dataset.filename }}</h3>
          <p>{{ dataset.description || 'No description available' }}</p>
          <p><strong>Categories:</strong> {{ dataset.categories || 'Not specified' }}</p>
          <p><strong>Size:</strong> {{ formatSize(dataset.size) }}</p>
          <el-button type="primary" @click="downloadDataset(dataset.filename)">Download</el-button>
        </div>
      </div>
      
      <!-- 添加分页组件 -->
      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next, jumper, ->, total"
        @current-change="handlePageChange"
        class="pagination"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const activeIndex = ref('1-1')
const planeDatasets = ref([])
const loading = ref(false)
const currentPage = ref(1)  // 当前页码
const pageSize = ref(10)   // 每页显示数量
const total = ref(0)       // 总记录数

const handleSelect = (key, keyPath) => {
  console.log(key, keyPath)
}

const goToPlaneDataset = () => {
  router.push('/dataset/plane')
}

const fetchPlaneDatasets = async (page = 1) => {
  try {
    loading.value = true
    const response = await axios.get('/api/datasets', {
      params: { 
        category_filter: 'plane',
        page: page,
        page_size: pageSize.value
      }
    })
    planeDatasets.value = response.data.datasets
    total.value = response.data.total || 0  // 假设后端返回total字段
  } catch (error) {
    console.error('Failed to fetch datasets:', error)
    planeDatasets.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

const downloadDataset = async (filename) => {
  try {
    const response = await axios({
      url: `/api/download/${filename}`,
      method: 'GET',
      responseType: 'blob',
    })
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Download failed:', error)
    alert('Failed to download dataset. Please try again.')
  }
}

const exploreSamples = () => {
  alert('Exploring sample images...')
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const handlePageChange = (newPage) => {
  currentPage.value = newPage
  fetchPlaneDatasets(newPage)
}

onMounted(() => {
  fetchPlaneDatasets(currentPage.value)
})
</script>

<style scoped>
/* 保持原有样式不变，添加分页样式 */
.pagination {
  margin-top: 30px;
  display: flex;
  justify-content: center;
}
</style>

<style scoped>
.plane-dataset-container {
min-height: 100vh;
background-color: #f5f7fa;
font-family: 'Arial', sans-serif;
}

.header {
display: flex;
justify-content: space-between;
align-items: center;
padding: 10px 50px;
background-color: #fff;
box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.logo {
font-size: 24px;
font-weight: bold;
color: #6b48ff;
}

.nav-menu {
flex-grow: 1;
margin-left: 50px;
background-color: transparent;
border-bottom: none;
}

.menu-icon {
width: 16px;
height: 16px;
margin-right: 8px;
vertical-align: middle;
}

.header-actions {
display: flex;
align-items: center;
gap: 15px;
}

.sign-in {
color: #606266;
font-size: 16px;
}

.demo-btn {
background-color: #fff;
border: 1px solid #6b48ff;
color: #6b48ff;
}

.start-btn {
background-color: #6b48ff;
border-color: #6b48ff;
}

.dataset-section {
text-align: center;
padding: 50px 20px;
}

.dataset-section h1 {
font-size: 48px;
font-weight: bold;
color: #1f2a44;
margin-bottom: 20px;
}

.dataset-section p {
font-size: 18px;
color: #606266;
margin-bottom: 30px;
max-width: 800px;
margin-left: auto;
margin-right: auto;
}

.dataset-actions {
display: flex;
justify-content: center;
gap: 20px;
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
justify-content: center;
gap: 20px;
}

.image-grid img {
width: 300px;
height: 200px;
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
margin-bottom: 30px;
}

.download-items {
display: flex;
flex-direction: column;
align-items: center;
gap: 20px;
}

.download-item {
background-color: #fff;
padding: 20px;
border-radius: 10px;
box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
width: 100%;
max-width: 800px;
text-align: left;
}

.download-item h3 {
font-size: 24px;
color: #1f2a44;
margin-bottom: 10px;
}

.download-item p {
font-size: 16px;
color: #606266;
margin-bottom: 10px;
}

.loading {
font-size: 18px;
color: #606266;
}

.no-data {
font-size: 18px;
color: #909399;
}
</style>
