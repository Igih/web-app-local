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
          <img src="/icons/home.svg" alt="Home Icon" class="menu-icon" />
          <span>Home</span>
        </el-menu-item>
        <el-sub-menu index="1" :class="{ 'is-active': activeIndex === '1' }">
          <template #title>
            <img src="/icons/database-sync.svg" alt="Database-sync Icon" class="menu-icon" />
            <span>Datasets</span>
          </template>
          <el-menu-item
            v-for="category in categories"
            :key="category.id"
            @click="goToCategory(category.name)"
          >
            <span>{{ category.name }}</span>
          </el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="2">
          <template #title>
            <img src="/icons/lightbulb-on-30.svg" alt="Lightbulb-on Icon" class="menu-icon" />
            <span>Solutions</span>
          </template>
          <el-menu-item index="2-1">YOLOV</el-menu-item>
          <el-menu-item index="2-2">LLM</el-menu-item>
          <el-menu-item index="2-3">Stable Diffusion</el-menu-item>
        </el-sub-menu>
        <el-sub-menu index="3">
          <template #title>
            <img src="/icons/book-open.svg" alt="Book-open Icon" class="menu-icon" />
            <span>Resource</span>
          </template>
          <el-menu-item index="3-1">
            <span>Drone</span>
          </el-menu-item>
          <el-menu-item index="3-2">
            <span>Atlas</span>
          </el-menu-item>
        </el-sub-menu>
        <el-menu-item index="9" @click="goToUserGuide">
          <img src="/icons/youtube.svg" alt="Video Icon" class="menu-icon" />
          <span>User Guide</span>
        </el-menu-item>
        <el-menu-item 
          index="7" 
          @click="goToUserDatasetManager"
          v-if="authStore.currentUser && authStore.currentUser.role === 'user'"
        >
          <img src="/icons/database-arrow-up.svg" alt="Database Icon" class="menu-icon" />
          <span>My Data</span>
        </el-menu-item>
        <el-menu-item 
          v-if="authStore.currentUser && authStore.currentUser.role === 'user'"
          index="8" 
          @click="goToMarkdownEditor"
        >
          <img src="/icons/pencil-outline.svg" alt="Pencil Icon" class="menu-icon" />
          <span>My Notes</span>
        </el-menu-item>
        <el-menu-item 
          index="5" 
          @click="goToFilePreview"
          v-if="authStore.currentUser && authStore.currentUser.role === 'user'"
          >
          <img src="/icons/file-document-outline.svg" alt="File-document Icon" class="menu-icon" />
          <span>Browse Files</span>
        </el-menu-item>
        <el-menu-item 
          v-if="authStore.currentUser && authStore.currentUser.role === 'admin'" 
          index="6" 
          @click="goToDatasetManager"
        >
          <img src="/icons/cog-refresh-outline.svg" alt="Cog-refresh Icon" class="menu-icon" />
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
              <el-dropdown-item 
                v-if="authStore.currentUser && authStore.currentUser.role === 'admin'" 
                command="create-user"
              >
                Create User
              </el-dropdown-item>
              <el-dropdown-item 
                v-if="authStore.currentUser && authStore.currentUser.role === 'admin'" 
                command="reset-password"
              >
                Reset User Password
              </el-dropdown-item>
              <el-dropdown-item command="change-password">Change Password</el-dropdown-item>
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

    <!-- 修改密码对话框 -->
    <el-dialog v-model="changePasswordDialogVisible" title="Change Password" width="30%">
      <el-form :model="changePasswordForm" label-width="120px" :rules="passwordRules" ref="changePasswordFormRef">
        <el-form-item label="Current Password" prop="currentPassword">
          <el-input v-model="changePasswordForm.currentPassword" type="password" autocomplete="off" />
        </el-form-item>
        <el-form-item label="New Password" prop="newPassword">
          <el-input v-model="changePasswordForm.newPassword" type="password" autocomplete="off" />
        </el-form-item>
        <el-form-item label="Confirm Password" prop="confirmPassword">
          <el-input v-model="changePasswordForm.confirmPassword" type="password" autocomplete="off" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="changePasswordDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="handleChangePassword">Submit</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 新增用户对话框 -->
    <el-dialog v-model="createUserDialogVisible" title="Create User" width="30%">
      <el-form :model="createUserForm" label-width="120px" :rules="createUserRules" ref="createUserFormRef">
        <el-form-item label="Username" prop="username">
          <el-input v-model="createUserForm.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="Password" prop="password">
          <el-input v-model="createUserForm.password" type="password" autocomplete="off" />
        </el-form-item>
        <el-form-item label="Confirm Password" prop="confirmPassword">
          <el-input v-model="createUserForm.confirmPassword" type="password" autocomplete="off" />
        </el-form-item>
        <el-form-item label="Role" prop="role">
          <el-select v-model="createUserForm.role" placeholder="Select role">
            <el-option label="Admin" value="admin" />
            <el-option label="User" value="user" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="createUserDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="handleCreateUser">Create</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 重置用户密码对话框 -->
    <el-dialog v-model="resetPasswordDialogVisible" title="Reset User Password" width="30%">
      <el-form :model="resetPasswordForm" label-width="120px" :rules="resetPasswordRules" ref="resetPasswordFormRef">
        <el-form-item label="Username" prop="username">
          <el-input v-model="resetPasswordForm.username" autocomplete="off" />
        </el-form-item>
        <el-form-item label="New Password" prop="newPassword">
          <el-input v-model="resetPasswordForm.newPassword" type="password" autocomplete="off" />
        </el-form-item>
        <el-form-item label="Confirm Password" prop="confirmPassword">
          <el-input v-model="resetPasswordForm.confirmPassword" type="password" autocomplete="off" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="resetPasswordDialogVisible = false">Cancel</el-button>
          <el-button type="primary" @click="handleResetPassword">Reset</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { ArrowDown } from '@element-plus/icons-vue'
import axios from 'axios'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const categories = ref([])
const loginDialogVisible = ref(false)
const changePasswordDialogVisible = ref(false)
const createUserDialogVisible = ref(false)
const resetPasswordDialogVisible = ref(false)
const changePasswordFormRef = ref(null)
const createUserFormRef = ref(null)
const resetPasswordFormRef = ref(null)

const loginForm = ref({
  username: '',
  password: ''
})

const changePasswordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const createUserForm = ref({
  username: '',
  password: '',
  confirmPassword: '',
  role: ''
})

const resetPasswordForm = ref({
  username: '',
  newPassword: '',
  confirmPassword: ''
})

const passwordRules = {
  currentPassword: [
    { required: true, message: 'Please enter your current password', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: 'Please enter your new password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: 'Please confirm your new password', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== changePasswordForm.value.newPassword) {
          callback(new Error('Passwords do not match'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const createUserRules = {
  username: [
    { required: true, message: 'Please enter a username', trigger: 'blur' }
  ],
  password: [
    { required: true, message: 'Please enter a password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: 'Please confirm the password', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== createUserForm.value.password) {
          callback(new Error('Passwords do not match'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  role: [
    { required: true, message: 'Please select a role', trigger: 'change' }
  ]
}

const resetPasswordRules = {
  username: [
    { required: true, message: 'Please enter a username', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: 'Please enter a new password', trigger: 'blur' },
    { min: 6, message: 'Password must be at least 6 characters', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: 'Please confirm the new password', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== resetPasswordForm.value.newPassword) {
          callback(new Error('Passwords do not match'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

const activeIndex = computed(() => {
  if (route.path === '/') {
    return '0'
  } else if (route.path === '/dataset-manager') {
    return '6'
  } else if (route.path === '/user-dataset-manager') {
    return '7'
  } else if (route.path === '/markdown-editor') {
    return '8'
  } else if (route.path === '/user-guide') {
    return '9'
  } else if (route.path === '/folder') {
    return '5'
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
    train: 'mdi:train',
    bus: 'mdi:bus',
    bicycle: 'mdi:bicycle',
    motorcycle: 'mdi:motorbike',
    helicopter: 'mdi:helicopter',
    rocket: 'mdi:rocket',
    submarine: 'mdi:submarine',
    truck: 'mdi:truck',
    ambulance: 'mdi:ambulance',
    firetruck: 'mdi:fire-truck',
    police: 'mdi:police-car',
    taxi: 'mdi:taxi',
    tractor: 'mdi:tractor',
  }
  return iconMap[category.toLowerCase()] || 'mdi:database'
}

const goToCategory = (category) => {
  router.push(`/dataset/${category.toLowerCase()}`)
}

const goToMarkdownEditor = () => {
  router.push('/markdown-editor')
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

const goToUserGuide = () => {
  router.push('/user-guide')
}

const goToFilePreview = () => {
  router.push('/folder')
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
    ElMessage.error(error.response?.data?.detail || 'Login failed: username or password incorrect')
  }
}

const handleChangePassword = async () => {
  try {
    await changePasswordFormRef.value.validate()
    const response = await axios.post('/api/change-password', {
      current_password: changePasswordForm.value.currentPassword,
      new_password: changePasswordForm.value.newPassword
    })
    ElMessage.success('Password changed successfully')
    changePasswordDialogVisible.value = false
    changePasswordForm.value = {
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to change password')
  }
}

const handleCreateUser = async () => {
  try {
    await createUserFormRef.value.validate()
    const response = await axios.post('/api/create-user', {
      username: createUserForm.value.username,
      password: createUserForm.value.password,
      role: createUserForm.value.role
    })
    ElMessage.success('User created successfully')
    createUserDialogVisible.value = false
    createUserForm.value = {
      username: '',
      password: '',
      confirmPassword: '',
      role: ''
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to create user')
  }
}

const handleResetPassword = async () => {
  try {
    await resetPasswordFormRef.value.validate()
    const response = await axios.post('/api/reset-password', {
      username: resetPasswordForm.value.username,
      new_password: resetPasswordForm.value.newPassword
    })
    ElMessage.success('Password reset successfully')
    resetPasswordDialogVisible.value = false
    resetPasswordForm.value = {
      username: '',
      newPassword: '',
      confirmPassword: ''
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || 'Failed to reset password')
  }
}

const handleUserCommand = (command) => {
  if (command === 'logout') {
    authStore.logout()
    ElMessage.success('Logout successful')
    router.push('/')
  } else if (command === 'change-password') {
    changePasswordDialogVisible.value = true
  } else if (command === 'create-user') {
    createUserDialogVisible.value = true
  } else if (command === 'reset-password') {
    resetPasswordDialogVisible.value = true
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