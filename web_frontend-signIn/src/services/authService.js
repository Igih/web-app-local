// services/authService.js
import axios from 'axios';
import { useAuthStore } from '@/stores/auth';
import { useRouter } from 'vue-router';

export async function login(username, password) {
  const authStore = useAuthStore();
  const router = useRouter();
  const params = new URLSearchParams({ username, password });
  
  try {
    const response = await axios.post('/api/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    authStore.login(response.data.access_token, username);
    
    // 根据上下文跳转
    if (router.currentRoute.value.path === '/') {
      router.push('/dataset-manager');
    }
    return response.data;
  } catch (error) {
    throw error; // 让调用者处理错误
  }
}

export async function verifyToken() {
  const authStore = useAuthStore();
  const token = localStorage.getItem('token');
  if (!token) {
    authStore.logout();
    return false;
  }
  try {
    const response = await axios.get('/api/verify-token');
    authStore.login(token, response.data.username); // 更新状态
    return true;
  } catch (error) {
    authStore.logout();
    return false;
  }
}

export function logout() {
  const authStore = useAuthStore();
  authStore.logout();
}