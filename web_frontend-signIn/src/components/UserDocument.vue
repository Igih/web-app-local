<template>
    <div class="user-dataset-manager">
      <!-- 顶部工具栏 -->
      <el-row class="toolbar" :gutter="20">
        <el-col :span="12">
          <el-button type="primary" @click="createNewMarkdown">
            <Icon icon="mdi:plus" class="btn-icon" /> New Markdown
          </el-button>
        </el-col>
        <el-col :span="12" class="search-col">
          <el-input
            v-model="searchQuery"
            placeholder="Search by title or content..."
            clearable
            @input="filterMarkdowns"
          >
            <template #prefix>
              <Icon icon="mdi:magnify" class="search-icon" />
            </template>
          </el-input>
        </el-col>
      </el-row>
  
      <!-- 主内容区域 -->
      <el-row class="main-content" :gutter="20">
        <!-- 左侧 Markdown 列表 -->
        <el-col :span="6" class="markdown-list">
          <el-table
            :data="filteredMarkdowns"
            style="width: 100%"
            @row-click="selectMarkdown"
            :row-class-name="tableRowClassName"
            height="calc(100vh - 200px)"
          >
            <el-table-column prop="title" label="Title" />
            <el-table-column prop="updated_at" label="Last Modified" width="150">
              <template #default="{ row }">
                {{ formatDate(row.updated_at) }}
              </template>
            </el-table-column>
            <el-table-column width="60">
              <template #default="{ row }">
                <el-popconfirm
                  title="Are you sure to delete this?"
                  @confirm="deleteMarkdown(row.id)"
                >
                  <template #reference>
                    <el-button type="danger" size="small" circle>
                      <Icon icon="mdi:delete" />
                    </el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-col>
  
        <!-- 右侧编辑/查看区域 -->
        <el-col :span="18" class="editor-container">
          <div v-if="selectedMarkdown" class="editor-wrapper">
            <!-- 编辑器工具栏 -->
            <el-row class="editor-toolbar">
              <el-col :span="12">
                <el-button-group>
                  <el-button @click="toggleViewMode('split')">
                    Split View
                  </el-button>
                  <el-button @click="toggleViewMode('edit')">
                    Edit Only
                  </el-button>
                  <el-button @click="toggleViewMode('preview')">
                    Preview Only
                  </el-button>
                </el-button-group>
              </el-col>
              <el-col :span="12" class="toolbar-right">
                <el-button @click="saveMarkdown" :disabled="!isEdited">
                  <Icon icon="mdi:content-save" /> Save
                </el-button>
                <el-button @click="exportMarkdown">
                  <Icon icon="mdi:export" /> Export
                </el-button>
              </el-col>
            </el-row>
  
            <!-- 编辑器内容 -->
            <div class="editor-content" :class="viewMode">
              <textarea
                v-if="viewMode !== 'preview'"
                v-model="selectedMarkdown.content"
                placeholder="Write your Markdown here..."
                @input="handleContentChange"
              />
              <div
                v-if="viewMode !== 'edit'"
                class="preview"
                v-html="renderedMarkdown"
              />
            </div>
  
            <!-- 状态栏 -->
            <div class="status-bar">
              <span>Words: {{ wordCount }}</span>
              <span>Last Saved: {{ lastSaved }}</span>
              <span>{{ isEdited ? 'Unsaved Changes' : 'Saved' }}</span>
            </div>
          </div>
          <div v-else class="empty-state">
            <el-empty description="Select a Markdown or create a new one" />
          </div>
        </el-col>
      </el-row>
    </div>
  </template>
  
  <script setup>
  import { ref, computed, onMounted, watch } from 'vue'
  import { ElMessage, ElEmpty } from 'element-plus'
  import { Icon } from '@iconify/vue'
  import axios from 'axios'
  import { marked } from 'marked'
  import DOMPurify from 'dompurify'
  import { useAuthStore } from '@/stores/auth'
  
  const authStore = useAuthStore()
  const markdowns = ref([])
  const filteredMarkdowns = ref([])
  const selectedMarkdown = ref(null)
  const searchQuery = ref('')
  const viewMode = ref('split')
  const isEdited = ref(false)
  const lastSaved = ref('Never')
  
  // 加载 Markdown 列表
  const fetchMarkdowns = async () => {
    try {
      const response = await axios.get('/api/markdowns', {
        headers: { Authorization: `Bearer ${authStore.currentUser.token}` }
      })
      markdowns.value = response.data
      filteredMarkdowns.value = markdowns.value
    } catch (error) {
      ElMessage.error('Failed to load Markdowns')
    }
  }
  
  // 过滤 Markdown
  const filterMarkdowns = () => {
    const query = searchQuery.value.toLowerCase()
    filteredMarkdowns.value = markdowns.value.filter(
      (md) =>
        md.title.toLowerCase().includes(query) ||
        md.content.toLowerCase().includes(query)
    )
  }
  
  // 创建新 Markdown
  const createNewMarkdown = async () => {
    try {
      const response = await axios.post(
        '/api/markdowns',
        {
          title: 'Untitled',
          content: ''
        },
        { headers: { Authorization: `Bearer ${authStore.currentUser.token}` } }
      )
      markdowns.value.unshift(response.data)
      filteredMarkdowns.value = markdowns.value
      selectMarkdown(response.data)
      ElMessage.success('New Markdown created')
    } catch (error) {
      ElMessage.error('Failed to create Markdown')
    }
  }
  
  // 选择 Markdown
  const selectMarkdown = (row) => {
    selectedMarkdown.value = { ...row }
    isEdited.value = false
    lastSaved.value = formatDate(row.updated_at)
  }
  
  // 保存 Markdown
  const saveMarkdown = async () => {
    if (!selectedMarkdown.value) return
    try {
      await axios.put(
        `/api/markdowns/${selectedMarkdown.value.id}`,
        selectedMarkdown.value,
        { headers: { Authorization: `Bearer ${authStore.currentUser.token}` } }
      )
      const index = markdowns.value.findIndex(
        (md) => md.id === selectedMarkdown.value.id
      )
      markdowns.value[index] = { ...selectedMarkdown.value }
      filteredMarkdowns.value = markdowns.value
      isEdited.value = false
      lastSaved.value = formatDate(new Date())
      ElMessage.success('Markdown saved')
    } catch (error) {
      ElMessage.error('Failed to save Markdown')
    }
  }
  
  // 删除 Markdown
  const deleteMarkdown = async (id) => {
    try {
      await axios.delete(`/api/markdowns/${id}`, {
        headers: { Authorization: `Bearer ${authStore.currentUser.token}` } }
      )
      markdowns.value = markdowns.value.filter((md) => md.id !== id)
      filteredMarkdowns.value = markdowns.value
      if (selectedMarkdown.value?.id === id) {
        selectedMarkdown.value = null
      }
      ElMessage.success('Markdown deleted')
    } catch (error) {
      ElMessage.error('Failed to delete Markdown')
    }
  }
  
  // 切换视图模式
  const toggleViewMode = (mode) => {
    viewMode.value = mode
  }
  
  // 渲染 Markdown
  const renderedMarkdown = computed(() => {
    if (!selectedMarkdown.value) return ''
    return DOMPurify.sanitize(marked(selectedMarkdown.value.content))
  })
  
  // 计算字数
  const wordCount = computed(() => {
    if (!selectedMarkdown.value) return 0
    return selectedMarkdown.value.content.split(/\s+/).filter((w) => w).length
  })
  
  // 内容变化
  const handleContentChange = () => {
    isEdited.value = true
  }
  
  // 导出 Markdown
  const exportMarkdown = () => {
    if (!selectedMarkdown.value) return
    const blob = new Blob([selectedMarkdown.value.content], {
      type: 'text/markdown'
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${selectedMarkdown.value.title}.md`
    a.click()
    URL.revokeObjectURL(url)
  }
  
  // 格式化日期
  const formatDate = (date) => {
    return new Date(date).toLocaleString()
  }
  
  // 表格行类名
  const tableRowClassName = ({ row }) => {
    return selectedMarkdown.value?.id === row.id ? 'selected-row' : ''
  }
  
  // 自动保存
  watch(
    () => selectedMarkdown.value?.content,
    (newContent, oldContent) => {
      if (newContent !== oldContent && isEdited.value) {
        const timer = setTimeout(() => {
          saveMarkdown()
        }, 5000)
        return () => clearTimeout(timer)
      }
    },
    { deep: true }
  )
  
  onMounted(() => {
    fetchMarkdowns()
  })
  </script>
  
  <style scoped>
  .user-dataset-manager {
    padding: 20px;
    background-color: #f5f7fa;
    min-height: calc(100vh - 80px);
  }
  
  .toolbar {
    margin-bottom: 20px;
  }
  
  .btn-icon {
    margin-right: 5px;
  }
  
  .search-col {
    display: flex;
    justify-content: flex-end;
  }
  
  .search-icon {
    margin: 0 5px;
  }
  
  .markdown-list {
    background-color: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    padding: 10px;
  }
  
  .editor-container {
    background-color: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    padding: 10px;
    height: calc(100vh - 200px);
    display: flex;
    flex-direction: column;
  }
  
  .editor-wrapper {
    display: flex;
    flex-direction: column;
    height: 100%;
  }
  
  .editor-toolbar {
    padding: 10px;
    border-bottom: 1px solid #e8ecef;
  }
  
  .toolbar-right {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
  }
  
  .editor-content {
    flex: 1;
    display: flex;
    overflow: hidden;
  }
  
  .editor-content.split {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
  
  .editor-content.edit textarea {
    width: 100%;
  }
  
  .editor-content.preview .preview {
    width: 100%;
  }
  
  textarea {
    border: none;
    resize: none;
    padding: 15px;
    font-family: 'Arial', sans-serif;
    font-size: 14px;
    background-color: #f5f5f5;
    border-radius: 4px;
    outline: none;
    flex: 1;
  }
  
  .preview {
    padding: 15px;
    overflow-y: auto;
    background-color: #fff;
    border-left: 1px solid #e8ecef;
  }
  
  .preview :deep(h1, h2, h3, h4, h5, h6) {
    margin: 10px 0;
  }
  
  .preview :deep(p) {
    margin: 10px 0;
  }
  
  .preview :deep(code) {
    background-color: #f5f5f5;
    padding: 2px 4px;
    border-radius: 4px;
  }
  
  .preview :deep(pre) {
    background-color: #f5f5f5;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
  }
  
  .status-bar {
    padding: 10px;
    border-top: 1px solid #e8ecef;
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #606266;
  }
  
  .empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  :deep(.selected-row) {
    background-color: #e6f7ff !important;
  }
  </style>