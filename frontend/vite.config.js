
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'; // 显式从 'node:path' 导入

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      // 如果需要，可以添加别名，但通常不需要
      'pinia': '/node_modules/pinia',
      '@': path.resolve(__dirname, './src'), // 确保 @ 指向 src 目录
    },
  },
  server: {
    // proxy: {
    //   '/upload': 'http://localhost:8000',
    //   '/datasets': 'http://localhost:8000',
    //   '/download': 'http://localhost:8000'
    // }
  }

})