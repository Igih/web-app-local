<template>
  <div class="layout-container">
    <!-- 导航栏 -->
    <el-header class="header">
      <div class="logo" @click="goToHome">EIP</div>
      <el-menu
        :default-active="activeIndex"
        class="nav-menu"
        mode="horizontal"
        :ellipsis="false"
      >
        <el-menu-item index="0" @click="goToHome">
          <Icon icon="mdi:home" class="menu-icon" />
          <span>Home</span>
        </el-menu-item>
        <el-sub-menu index="1" :class="{ 'is-active': activeIndex === '1' }">
          <template #title>
            <Icon icon="mdi:database" class="menu-icon" />
            <span>Datasets</span>
          </template>
          <el-menu-item
            v-for="category in categories"
            :key="category.id"
            @click="goToCategory(category.name)"
          >
            <Icon :icon="category.icon" class="menu-icon" />
            <span>{{ category.name }}</span>
          </el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="2">
          <template #title>
            <Icon icon="mdi:lightbulb" class="menu-icon" />
            <span>Solutions</span>
          </template>
          <el-menu-item index="2-1">YOLOV</el-menu-item>
          <el-menu-item index="2-2">LLM</el-menu-item>
          <el-menu-item index="2-3">Stable Diffusion</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="3">
          <template #title>
            <Icon icon="mdi:book-open" class="menu-icon" />
            <span>Resource</span>
          </template>
          <el-menu-item index="3-1">
            <Icon icon="mdi:drone" class="menu-icon" />
            <span>Drone</span>
          </el-menu-item>
          <el-menu-item index="3-2">
            <Icon icon="mdi:map" class="menu-icon" />
            <span>Altlas</span>
          </el-menu-item>
        </el-sub-menu>
        <el-menu-item index="5">
          <Icon icon="mdi:document" class="menu-icon" />
          <span>Logs</span>
        </el-menu-item>
        <el-menu-item index="7" @click="goToUserDatasetManager">
          <Icon icon="mdi:account-data" class="menu-icon" />
          <span>My Data</span>
        </el-menu-item>
        <el-menu-item 
          v-if="authStore.currentUser && authStore.currentUser.role === 'admin'" 
          index="6" 
          @click="goToDatasetManager"
        >
          <Icon icon="mdi:cog" class="menu-icon" />
          <span>Admin</span>
        </el-menu-item>
      </el-menu>
      <div class="header-actions">
        <el-dropdown v-if="authStore.currentUser" @command="handleUserCommand">
          <span class="user-welcome">
            Welcome, {{ authStore.currentUser.username }}<el-icon><arrow-down /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">Logout</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-link v-else class="sign-in" :underline="false" @click="showLoginDialog">
          Sign In
        </el-link>
      </div>
    </el-header>

    <!-- 内容区域 -->
    <main>
      <router-view />
    </main>

    <!-- 登录对话框 -->
    <el-dialog v-model="loginDialogVisible" title="Login" width="30%">
      <el-form :model="loginForm" label-width="80px">
        <el-form-item label="Username">
          <el-input v-model="loginForm.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="Password">
          <el-input v-model="loginForm.password" type="password" autocomplete="off" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="loginDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="handleLogin">Login</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>
  
  <script setup>
  import { ref, onMounted, computed } from 'vue'
  import { useRouter, useRoute } from 'vue-router'
  import { Icon } from '@iconify/vue'
  import { ElMessage } from 'element-plus'
  import { useAuthStore } from '@/stores/auth'
  import { ArrowDown } from '@element-plus/icons-vue'
  import axios from 'axios'
  
  const router = useRouter()
  const route = useRoute()
  const authStore = useAuthStore()
  const categories = ref([])
  const loginDialogVisible = ref(false)
  const loginForm = ref({
    username: '',
    password: ''
  })
  
  const activeIndex = computed(() => {
  if (route.path === '/') {
    return '0'
  } else if (route.path === '/dataset-manager') {
    return '6'
  } else if (route.path === '/user-dataset-manager') {
    return '7'
  } else if (route.path.startsWith('/dataset/')) {
    return '1'
  }
  return '0'
})
  
  const fetchCategories = async () => {
    try {
      const response = await axios.get('/api/categories_show')
      categories.value = response.data.categories_show.map(item => ({
        id: item.id,
        name: item.category,
        icon: getCategoryIcon(item.category)
      }))
    } catch (error) {
      console.error('Failed to fetch categories:', error)
    }
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
  
  const goToCategory = (category) => {
    router.push(`/dataset/${category.toLowerCase()}`)
  }
  
  const goToDatasetManager = () => {
    if (authStore.currentUser && authStore.currentUser.role === 'admin') {
      router.push('/dataset-manager')
    } else {
      ElMessage.error('Access denied: Admin role required')
    }
  }

  const goToUserDatasetManager = () => {
  router.push('/user-dataset-manager')
}
  
  const goToHome = () => {
    router.push('/')
  }
  
  const showLoginDialog = () => {
    loginDialogVisible.value = true
  }
  
  const handleLogin = async () => {
    try {
      await authStore.login(loginForm.value)
      ElMessage.success('Login successful')
      loginDialogVisible.value = false
      loginForm.value = { username: '', password: '' }
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || 'Login failed')
    }
  }
  
  const handleUserCommand = (command) => {
    if (command === 'logout') {
      authStore.logout()
      ElMessage.success('Logout successful')
      router.push('/')
    }
  }
  
  onMounted(() => {
    fetchCategories()
  })
  </script>
  
  <style scoped>
  .layout-container {
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
    cursor: pointer;
    transition: color 0.3s;
  }
  
  .logo:hover {
    color: #4a2dcc;
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
    cursor: pointer;
    transition: color 0.3s;
  }
  
  .sign-in:hover {
    color: #409EFF;
  }
  
  .user-welcome {
    color: #67c23a;
    font-weight: 500;
    cursor: pointer;
    display: flex;
    align-items: center;
  }
  
  .user-welcome:hover {
    color: #85ce61;
  }
  
  .el-icon {
    margin-left: 5px;
  }
  
  main {
    padding: 20px;
  }
  </style>