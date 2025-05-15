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
    <div v-else class="empty-message">
      没有发现图片和文件~~
      <p>('.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif')</p>
      <p>(txt、 xml、 json)</p>
    </div>

    <div class="load-more" v-if="hasMore">
      <button @click="loadMore" :disabled="isLoading">{{ isLoading ? 'Loading...' : 'Load More' }}</button>
    </div>

    <div v-if="selectedImage || selectedText || selectedXml || selectedJson" class="modal" @click="selectedImage = null; selectedText = null; selectedXml = null; selectedJson = null">
      <img v-if="selectedImage" :src="selectedImage" alt="Full Image" class="full-image" />
      <div v-if="selectedText || selectedXml || selectedJson" class="text-preview">
        <pre>{{ selectedText || selectedXml || selectedJson }}</pre>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
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

    const breadcrumb = computed(() => currentPath.value.split('/').filter(segment => segment))

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
      } catch (error) {
        console.error('Error fetching folder:', error)
        if (error.response?.status === 401) {
          authStore.logout()
          router.push('/')
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
      } else if (item.is_text) {
        selectedText.value = await fetchTextContent(item.path)
      } else if (item.is_xml) {
        selectedXml.value = await fetchTextContent(item.path)
      } else if (item.is_json) {
        selectedJson.value = await fetchTextContent(item.path)
      }
    }

    onMounted(() => {
      const initialPath = route.query.path || ''
      navigateTo(initialPath)
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
      navigateTo,
      handleItemClick,
      loadMore
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

.empty-message {
  text-align: center;
  font-size: 18px;
  color: #666;
  margin: 20px 0;
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
  white-space: nowrap; /* Prevent text wrapping */
  overflow: hidden; /* Hide overflowing text */
  text-overflow: ellipsis; /* Show ellipsis for truncated text */
  max-width: 100%; /* Ensure text stays within container */
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
}

.full-image {
  max-width: 90%;
  max-height: 90%;
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