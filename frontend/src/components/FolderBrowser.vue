<template>
  <div class="folder-browser">
    <div class="breadcrumb-box">
      <div class="breadcrumb">
        <span @click="navigateTo('')" :class="{ 'breadcrumb-item': true, 'selected': !breadcrumb.length }">/data</span>
        <span v-for="(segment, index) in breadcrumb" :key="index">
          / <span @click="navigateTo(breadcrumb.slice(0, index + 1).join('/'))" :class="{ 'breadcrumb-item': true, 'selected': index === breadcrumb.length - 1 }">{{ segment }}</span>
        </span>
      </div>
    </div>

    <div class="path-input">
      <input v-model="inputPath" placeholder="以/data开头, 输入绝对路径" @keyup.enter="navigateTo(inputPath)" />
      <button @click="navigateTo(inputPath)">Go</button>
    </div>

    <div class="file-counts">
      <span>文件夹: {{ totalFolders }}</span>
      <span>图片: {{ totalImages }}</span>
      <span>文本: {{ totalTexts }}</span>
    </div>

    <div v-if="isLoading && items.length === 0" class="loading-message">
      正在加载～～
    </div>
    <div v-else-if="items.length > 0" class="item-grid">
      <div v-for="item in items" :key="item.path" class="item" @click="handleItemClick(item)">
        <img v-if="item.thumbnail && !item.is_oversized && !item.is_corrupted" :src="item.thumbnail" alt="Thumbnail" class="thumbnail" loading="lazy"/>
        <span v-else class="icon">{{ item.is_directory ? '📁' : item.is_text || item.is_xml || item.is_json ? '📝' : '📄' }}</span>
        <p :title="item.name">{{ item.name }}</p>
        <p v-if="item.is_corrupted" class="corrupted-message">文件损坏</p>
        <p v-else-if="item.is_oversized" class="oversized-message">文件过大</p>
      </div>
    </div>
    <div v-else-if="totalItems > 100000" class="error-message">
      文件数量过多（超过100,000），请尝试访问子文件夹
    </div>
    <div v-else class="empty-message">
      没有发现图片和文件~~
      <p>('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif')</p>
      <p>(txt、 xml、 json)</p>
    </div>

    <div class="load-more" v-if="hasMore">
      <button @click="loadMore" :disabled="isLoading">{{ isLoading ? 'Loading...' : 'Load More' }}</button>
    </div>

    <div v-if="selectedImage || selectedText || selectedXml || selectedJson" class="modal" @click="closeModal">
      <div class="image-preview" v-if="selectedImage" @click.stop>
        <button class="nav-arrow left" @click="prevImage" :disabled="!hasPrevImage">◄</button>
        <img :src="selectedImage" alt="Full Image" class="full-image" />
        <div class="image-info">
          <p class="image-filename" :title="selectedImageName || 'Filename unavailable'">
            {{ selectedImageName || 'Filename unavailable' }}
          </p>
          <button v-if="showMoreInfoBtn" class="more-info-btn" @click="fetchImageInfo">More Info</button>
          <div v-if="showImageInfo" class="image-metadata">
            <p v-if="selectedImageResolution && selectedImageFileSize">
              Resolution: {{ selectedImageResolution }} | Size: {{ selectedImageFileSize }}
            </p>
            <p v-else>Metadata unavailable</p>
          </div>
        </div>
        <button class="nav-arrow right" @click="nextImage" :disabled="!hasNextImage">►</button>
      </div>
      <div v-if="selectedText || selectedXml || selectedJson" class="text-preview">
        <pre>{{ selectedText || selectedXml || selectedJson }}</pre>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'
import { useAuthStore } from '@/stores/auth'

export default {
  name: 'FolderBrowser',
  setup() {
    const router = useRouter()
    const route = useRoute()
    const authStore = useAuthStore()

    const currentPath = ref('')
    const items = ref([])
    const inputPath = ref('')
    const selectedImage = ref(null)
    const selectedImageName = ref(null)
    const selectedImageResolution = ref(null)
    const selectedImageFileSize = ref(null)
    const selectedText = ref(null)
    const selectedXml = ref(null)
    const selectedJson = ref(null)
    const page = ref(1)
    const pageSize = 100
    const hasMore = ref(false)
    const isLoading = ref(false)
    const totalItems = ref(0)
    const selectedImageIndex = ref(-1)
    const totalFolders = ref(0)
    const totalImages = ref(0)
    const totalTexts = ref(0)
    const showImageInfo = ref(false)
    const showMoreInfoBtn = ref(true) // 新增：控制“More Info”按钮显示

    const breadcrumb = computed(() => currentPath.value.split('/').filter(segment => segment))
    const imageItems = computed(() => items.value.filter(item => item.thumbnail))
    const hasPrevImage = computed(() => selectedImageIndex.value > 0)
    const hasNextImage = computed(() => selectedImageIndex.value < imageItems.value.length - 1)

    const observeImages = () => {
      const images = document.querySelectorAll('.thumbnail')
      const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target
            img.addEventListener('load', () => {
              // console.log(`Image loaded: ${img.src}`)
            }, { once: true })
            observer.unobserve(img)
          }
        })
      }, { rootMargin: '100px' })

      images.forEach(img => observer.observe(img))
    }

    const fetchFolderContent = async (path = '', pageNum = 1, append = false) => {
      try {
        isLoading.value = true
        const response = await axios.get('/api/folder', {
          params: { path, page: pageNum, page_size: pageSize },
          headers: { Authorization: `Bearer ${authStore.token}` }
        })
        currentPath.value = response.data.current_path
        if (append) {
          items.value = [...items.value, ...response.data.items]
        } else {
          items.value = response.data.items
        }
        hasMore.value = response.data.has_more
        totalItems.value = response.data.total_items
        totalFolders.value = response.data.total_folders
        totalImages.value = response.data.total_images
        totalTexts.value = response.data.total_texts
        selectedImageIndex.value = -1
      } catch (error) {
        console.error('Error fetching folder:', error)
        if (error.response?.status === 401) {
          authStore.logout()
          router.push('/')
        } else {
          items.value = []
          hasMore.value = false
          totalItems.value = 0
          totalFolders.value = 0
          totalImages.value = 0
          totalTexts.value = 0
        }
      } finally {
        isLoading.value = false
      }
    }

    const fetchTextContent = async (path) => {
      try {
        const response = await axios.get('/api/file/content', {
          params: { path },
          headers: { Authorization: `Bearer ${authStore.token}` }
        })
        return response.data.content
      } catch (error) {
        console.error('Error fetching content:', error)
        if (error.response?.status === 400 && error.response.data.detail.includes('corrupted')) {
          return '文件损坏，无法读取内容'
        } else if (error.response?.status === 400) {
          return '文件大小超过1MB，无法读取'
        } else if (error.response?.status === 404) {
          return '文件不存在'
        } else {
          return '无法加载文件内容，请稍后重试'
        }
      }
    }

    const fetchImageInfo = async () => {
      try {
        const path = imageItems.value[selectedImageIndex.value].path
        const response = await axios.get('/api/image/info', {
          params: { path },
          headers: { Authorization: `Bearer ${authStore.token}` }
        })
        selectedImageResolution.value = response.data.resolution
        selectedImageFileSize.value = response.data.file_size
        showImageInfo.value = true
        showMoreInfoBtn.value = false // 隐藏“More Info”按钮
      } catch (error) {
        console.error('Error fetching image info:', error)
        selectedImageResolution.value = null
        selectedImageFileSize.value = null
        showImageInfo.value = true
        showMoreInfoBtn.value = false // 即使出错也隐藏按钮
      }
    }

    const navigateTo = (path) => {
      inputPath.value = path
      page.value = 1
      items.value = []
      fetchFolderContent(path, 1)
    }

    const loadMore = () => {
      page.value += 1
      fetchFolderContent(currentPath.value, page.value, true)
    }

    const handleItemClick = async (item) => {
      if (item.is_corrupted) {
        alert('无法预览：文件已损坏')
        return
      }
      if (item.is_oversized) {
        alert('无法预览：文件过大')
        return
      }
      if (item.is_directory) {
        navigateTo(item.path)
      } else if (item.thumbnail) {
        selectedImage.value = item.thumbnail
        selectedImageName.value = item.name
        selectedImageResolution.value = null
        selectedImageFileSize.value = null
        showImageInfo.value = false
        showMoreInfoBtn.value = true // 显示“More Info”按钮
        const index = imageItems.value.findIndex(img => img.path === item.path)
        selectedImageIndex.value = index
      } else if (item.is_text) {
        selectedText.value = await fetchTextContent(item.path)
      } else if (item.is_xml) {
        selectedXml.value = await fetchTextContentiterals(item.path)
      } else if (item.is_json) {
        selectedJson.value = await fetchTextContent(item.path)
      }
    }

    const prevImage = () => {
      if (hasPrevImage.value) {
        selectedImageIndex.value -= 1
        selectedImage.value = imageItems.value[selectedImageIndex.value].thumbnail
        selectedImageName.value = imageItems.value[selectedImageIndex.value].name
        selectedImageResolution.value = null
        selectedImageFileSize.value = null
        showImageInfo.value = false
        showMoreInfoBtn.value = true // 显示“More Info”按钮
      }
    }

    const nextImage = () => {
      if (hasNextImage.value) {
        selectedImageIndex.value += 1
        selectedImage.value = imageItems.value[selectedImageIndex.value].thumbnail
        selectedImageName.value = imageItems.value[selectedImageIndex.value].name
        selectedImageResolution.value = null
        selectedImageFileSize.value = null
        showImageInfo.value = false
        showMoreInfoBtn.value = true // 显示“More Info”按钮
      }
    }

    const closeModal = () => {
      selectedImage.value = null
      selectedImageName.value = null
      selectedImageResolution.value = null
      selectedImageFileSize.value = null
      selectedText.value = null
      selectedXml.value = null
      selectedJson.value = null
      selectedImageIndex.value = -1
      showImageInfo.value = false
      showMoreInfoBtn.value = true // 重置为显示“More Info”按钮
    }

    const handleKeydown = (event) => {
      if (selectedImage.value || selectedText.value || selectedXml.value || selectedJson.value) {
        if (event.key === 'Escape') {
          closeModal()
        } else if (selectedImage.value) {
          if (event.key === 'ArrowLeft' && hasPrevImage.value) {
            prevImage()
          } else if (event.key === 'ArrowRight' && hasNextImage.value) {
            nextImage()
          }
        }
      }
    }

    onMounted(() => {
      const initialPath = route.query.path || ''
      navigateTo(initialPath)
      window.addEventListener('keydown', handleKeydown)
      observeImages()
    })

    onUnmounted(() => {
      window.removeEventListener('keydown', handleKeydown)
    })

    return {
      currentPath,
      items,
      inputPath,
      breadcrumb,
      selectedImage,
      selectedImageName,
      selectedImageResolution,
      selectedImageFileSize,
      selectedText,
      selectedXml,
      selectedJson,
      hasMore,
      isLoading,
      totalItems,
      navigateTo,
      handleItemClick,
      loadMore,
      prevImage,
      nextImage,
      hasPrevImage,
      hasNextImage,
      closeModal,
      imageItems,
      totalFolders,
      totalImages,
      totalTexts,
      fetchImageInfo,
      showImageInfo,
      showMoreInfoBtn
    }
  }
}
</script>

<style scoped>
.folder-browser {
  padding: 20px;
}

.breadcrumb-box {
  border: 1px solid #ddd;
  border-radius: 5px;
  padding: 8px;
  margin-bottom: 10px;
  display: inline-block;
}

.breadcrumb {
  margin-bottom: 0;
}

.breadcrumb-item {
  cursor: pointer;
  color: black;
}

.breadcrumb-item:hover {
  text-decoration: underline;
}

.breadcrumb-item.selected {
  font-weight: bold;
}

.path-input {
  margin-bottom: 10px;
}

.path-input input {
  padding: 5px;
  width: 300px;
}

.path-input button {
  padding: 5px 10px;
  margin-left: 10px;
}

.file-counts {
  margin-bottom: 20px;
  font-size: 14px;
  color: #333;
}

.file-counts span {
  margin-right: 20px;
}

.item-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}

.loading-message, .empty-message, .error-message {
  text-align: center;
  font-size: 18px;
  color: #666;
  margin: 20px 0;
}

.loading-message {
  color: #333;
}

.error-message {
  color: #d32f2f;
}

.item {
  text-align: center;
  cursor: pointer;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 5px;
  overflow: hidden;
}

.item p {
  margin: 5px 0 0 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.thumbnail {
  max-width: 100px;
  max-height: 100px;
  object-fit: cover;
}

.icon {
  font-size: 50px;
}

.modal {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  overflow: auto;
}

.image-preview {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.full-image {
  display: block;
}

.image-info {
  text-align: center;
  margin-top: 10px;
}

.image-filename {
  color: white;
  font-size: 16px;
  max-width: 80%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.image-metadata {
  color: white;
  font-size: 14px;
  margin-top: 5px;
}

.more-info-btn {
  padding: 5px 10px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  margin-top: 10px;
}

.more-info-btn:hover {
  background-color: #0056b3;
}

.nav-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  background: rgba(255, 255, 255, 0.7);
  border: none;
  font-size: 24px;
  padding: 10px;
  cursor: pointer;
  border-radius: 5px;
}

.nav-arrow.left {
  left: 20px;
}

.nav-arrow.right {
  right: 20px;
}

.nav-arrow:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.nav-arrow:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.9);
}

.nav-arrow:focus {
  outline: 2px solid #007bff;
  outline-offset: 2px;
}

.text-preview {
  background: white;
  padding: 20px;
  max-width: 80%;
  max-height: 80%;
  overflow-y: auto;
  border-radius: 5px;
}

.text-preview pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.load-more {
  text-align: center;
  margin-top: 20px;
}

.load-more button {
  padding: 10px 20px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
}

.load-more button:hover {
  background-color: #0056b3;
}

.load-more button:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.corrupted-message {
  color: red;
  font-size: 12px;
  margin-top: 5px;
}

.oversized-message {
  color: orange;
  font-size: 12px;
  margin-top: 5px;
}
</style>