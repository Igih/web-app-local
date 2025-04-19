// stores/upload.js
import { defineStore } from 'pinia'

export const useUploadStore = defineStore('upload', {
  state: () => ({
    isUploading: false,
    uploadProgress: 0,
    uploadSpeed: '0 KB/s',
    controller: null,
    lastUploadTime: null,
    lastLoaded: 0
  }),
  actions: {
    startUpload() {
      this.isUploading = true
      this.uploadProgress = 0
      this.uploadSpeed = '0 KB/s'
      this.controller = new AbortController()
      this.lastUploadTime = Date.now()
      this.lastLoaded = 0
    },
    updateProgress(loaded, total) {
      this.uploadProgress = Math.min(100, Math.round((loaded / total) * 100))
      this.calculateSpeed(loaded)
    },
    calculateSpeed(loaded) {
      const currentTime = Date.now()
      const timeDiff = (currentTime - this.lastUploadTime) / 1000
      const loadedDiff = loaded - this.lastLoaded
      let speed = loadedDiff / timeDiff / 1024 // KB/s
      
      let speedStr = ''
      if (speed>=1024*1024) {
        speed = speed / 1024 / 1024 // 转换为GB/s
        speedStr = `${speed.toFixed(2)} GB/s`
      }
      else if (speed >= 1024) {
        speed = speed / 1024 // 转换为MB/s
        speedStr = `${speed.toFixed(2)} MB/s`
      } else {
        speedStr = `${speed.toFixed(2)} KB/s`
      }
      
      this.uploadSpeed = speedStr
      this.lastLoaded = loaded
      this.lastUploadTime = currentTime
    },
    finishUpload() {
      this.isUploading = false
      this.uploadProgress = 0
      this.uploadSpeed = '0 KB/s'
      this.controller = null
    },
    cancelUpload() {
      if (this.controller) {
        this.controller.abort()
      }
      this.finishUpload()
    }
  }
})