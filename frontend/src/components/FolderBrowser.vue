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

    <div v-if="items.length > 0" class="item-grid">
      <div v-for="item in items" :key="item.path" class="item" @click="handleItemClick(item)">
        <img v-if="item.thumbnail" :src="item.thumbnail" alt="Thumbnail" class="thumbnail" loading="lazy"/>
        <span v-else class="icon">{{ item.is_directory ? '📁' : item.is_text || item.is_xml || item.is_json ? '📝' : '📄' }}</span>
        <p :title="item.name">{{ item.name }}</p>
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
    const selectedText = ref(null)
    const selectedXml = ref(null)
    const selectedJson = ref(null)
    const page = ref(1)
    const pageSize = 100
    const hasMore = ref(false)
    const isLoading = ref(false)
    const totalItems = ref(0)
    const selectedImageIndex = ref(-1) // Track the index of the current image

    const breadcrumb = computed(() => currentPath.value.split('/').filter(segment => segment))

    // Compute the list of images in the current folder
    const imageItems = computed(() => items.value.filter(item => item.thumbnail))

    // Check if there is a previous image
    const hasPrevImage = computed(() => selectedImageIndex.value > 0)

    // Check if there is a next image
    const hasNextImage = computed(() => selectedImageIndex.value < imageItems.value.length - 1)

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
        // Reset selected image index when folder content changes
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
        return 'Error loading content'
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
      if (item.is_directory) {
        navigateTo(item.path)
      } else if (item.thumbnail) {
        selectedImage.value = item.thumbnail
        selectedImageIndex.value = imageItems.value.findIndex(img => img.thumbnail === item.thumbnail)
      } else if (item.is_text) {
        selectedText.value = await fetchTextContent(item.path)
      } else if (item.is_xml) {
        selectedXml.value = await fetchTextContent(item.path)
      } else if (item.is_json) {
        selectedJson.value = await fetchTextContent(item.path)
      }
    }

    const prevImage = () => {
      if (hasPrevImage.value) {
        selectedImageIndex.value -= 1
        selectedImage.value = imageItems.value[selectedImageIndex.value].thumbnail
 caries
      }
    }

    const nextImage = () => {
      if (hasNextImage.value) {
        selectedImageIndex.value += 1
        selectedImage.value = imageItems.value[selectedImageIndex.value].thumbnail
      }
    }

    const closeModal = () => {
      selectedImage.value = null
      selectedText.value = null
      selectedXml.value = null
      selectedJson.value = null
      selectedImageIndex.value = -1
    }

    // Keyboard navigation for left/right arrows and escape key
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
      // Add keyboard event listener
      window.addEventListener('keydown', handleKeydown)
    })

    onUnmounted(() => {
      // Remove keyboard event listener
      window.removeEventListener('keydown', handleKeydown)
    })

    return {
      currentPath,
      items,
      inputPath,
      breadcrumb,
      selectedImage,
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
      closeModal
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
  margin-bottom: 20px;
}

.path-input input {
  padding: 5px;
  width: 300px;
}

.path-input button {
  padding: 5px 10px;
  margin-left: 10px;
}

.item-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}

.empty-message, .error-message {
  text-align: center;
  font-size: 18px;
  color: #666;
  margin: 20px 0;
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
  overflow: auto; /* Enable scrolling for large images */
}

.image-preview {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.full-image {
  display: block; /* Keep original image size */
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
</style>