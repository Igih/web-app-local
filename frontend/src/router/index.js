import { createRouter, createWebHistory } from 'vue-router'
import Layout from '@/components/Layout.vue'
import HomePage from '@/components/HomePage.vue'
import DatasetManager from '@/components/DatasetManager.vue'
import DatasetView from '@/components/DatasetView.vue'
import UserDatasetManager from '@/components/UserDatasetManager.vue'
import UserDocument from '@/components/UserDocument.vue'
import VideoPlayer  from '@/components/VideoPlayer.vue'
import FolderBrowser from '@/components/FolderBrowser.vue'
import AssetImport from '@/views/assets/AssetImport.vue'
import AssetImageManager from '@/views/assets/AssetImageManager.vue'
import AssetImportRecords from '@/views/assets/AssetImportRecords.vue'
import AssetOverview from '@/views/assets/AssetOverview.vue'
import AssetQualityDashboard from '@/views/assets/AssetQualityDashboard.vue'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    component: Layout,
    children: [
      { path: '', name: 'Home', component: HomePage },
      { path: 'dataset-manager', name: 'DatasetManager', component: DatasetManager },
      { path: 'dataset/:category', name: 'DatasetView', component: DatasetView, props: true },
      { path: 'user-dataset-manager', name: 'UserDatasetManager', component: UserDatasetManager },
      { path: 'markdown-editor', name: 'UserDocument', component: UserDocument },
      { path: 'user-guide', name: 'UserGuide', component: VideoPlayer },
      { path: 'folder', name: 'FolderBrowser', component: FolderBrowser }, // 新增路由
      { path: 'assets/import', name: 'AssetImport', component: AssetImport },
      { path: 'assets/images', name: 'AssetImageManager', component: AssetImageManager },
      { path: 'assets/records', name: 'AssetImportRecords', component: AssetImportRecords },
      { path: 'assets/overview', name: 'AssetOverview', component: AssetOverview },
      {
        path: 'assets/quality/:batchId',
        name: 'AssetQualityDashboard',
        component: AssetQualityDashboard,
        props: true,
      },
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// router.beforeEach((to, from, next) => {
//   const authStore = useAuthStore()
//   console.log('Navigating to:', to.path, 'User:', authStore.currentUser) // Debug
//   if (to.path === '/dataset-manager') {
//     if (!authStore.currentUser || authStore.currentUser.role !== 'admin') {
//       console.log('Redirecting to /: Not admin')
//       next('/')
//     } else {
//       next()
//     }
//   } else if (to.path.startsWith('/dataset/') && !authStore.currentUser) {
//     console.log('Redirecting to /: Not authenticated')
//     next('/')
//   } else {
//     next()
//   }
// })


export default router
