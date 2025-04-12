// @/stores/auth.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref(null)
  const token = ref(null) // 新增 token 状态

  // 初始化时检查 localStorage
  const init = () => {
    const savedUser = localStorage.getItem('currentUser')
    const savedToken = localStorage.getItem('token') // 从 localStorage 获取 token
    if (savedUser) {
      currentUser.value = JSON.parse(savedUser)
    }
    if (savedToken) {
      token.value = savedToken
    }
  }

  // 登录方法
  const login = async (credentials) => {
    const response = await axios.post('/api/login', credentials)
    currentUser.value = response.data.user
    token.value = response.data.access_token // 存储 token
    localStorage.setItem('currentUser', JSON.stringify(currentUser.value))
    localStorage.setItem('token', token.value) // 将 token 存入 localStorage
  }

  // 登出方法
  const logout = () => {
    currentUser.value = null
    token.value = null // 清除 token
    localStorage.removeItem('currentUser')
    localStorage.removeItem('token')
  }

  // 初始化 store
  init()

  return {
    currentUser,
    token, // 暴露 token
    login,
    logout
  }
})