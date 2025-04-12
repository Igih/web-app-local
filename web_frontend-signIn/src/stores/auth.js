// @/stores/auth.js
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

export const useAuthStore = defineStore('auth', () => {
  const currentUser = ref(null)
  
  // 初始化时检查localStorage
  const init = () => {
    const savedUser = localStorage.getItem('currentUser')
    if (savedUser) {
      currentUser.value = JSON.parse(savedUser)
    }
  }
  
  // 登录方法
  const login = async (credentials) => {
    const response = await axios.post('/api/login', credentials)
    currentUser.value = response.data.user
    localStorage.setItem('currentUser', JSON.stringify(currentUser.value))
  }
  
  // 登出方法
  const logout = () => {
    currentUser.value = null
    localStorage.removeItem('currentUser')
  }
  
  // 初始化store
  init()
  
  return {
    currentUser,
    login,
    logout
  }
})