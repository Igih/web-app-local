import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import router from './router'
import 'element-plus/dist/index.css'
import App from './App.vue'
import axios from 'axios';
import { createPinia } from 'pinia'; // 导入 Pinia
import { useAuthStore } from '@/stores/auth';

const app = createApp(App)
const pinia = createPinia();

app.use(ElementPlus);
app.use(pinia);
app.use(router);

// 配置 Axios 拦截器
axios.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, error => Promise.reject(error));

axios.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      const authStore = useAuthStore();
      authStore.logout();
      router.push('/');
      ElMessage.error('Session expired, please login again');
    }
    return Promise.reject(error);
  }
);


app.mount('#app')