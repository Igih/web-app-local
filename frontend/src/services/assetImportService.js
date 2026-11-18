import axios from 'axios'

export async function scanAssetImport(payload) {
  const response = await axios.post('/api/assets/imports/scan', payload)
  return response.data
}

export async function getAssetImportPreview(batchId) {
  const response = await axios.get(`/api/assets/imports/${batchId}/preview`)
  return response.data
}

export async function confirmAssetImport(batchId) {
  const response = await axios.post(`/api/assets/imports/${batchId}/confirm`)
  return response.data
}

export async function getAssetCategories() {
  const response = await axios.get('/api/assets/categories')
  return response.data.categories
}
