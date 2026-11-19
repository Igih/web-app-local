import axios from 'axios'

export async function listAssetImages(params) {
  const response = await axios.get('/api/assets/images', { params })
  return response.data
}

export async function getAssetImage(imageId) {
  const response = await axios.get(`/api/assets/images/${imageId}`)
  return response.data
}

export async function updateAssetImage(imageId, payload) {
  const response = await axios.patch(`/api/assets/images/${imageId}`, payload)
  return response.data
}

export async function batchUpdateAssetImages(payload) {
  const response = await axios.post('/api/assets/images/batch', payload)
  return response.data
}

export async function deleteAssetImage(imageId) {
  const response = await axios.delete(`/api/assets/images/${imageId}`)
  return response.data
}

export async function batchDeleteAssetImages(imageIds) {
  const response = await axios.post('/api/assets/images/batch-delete', {
    image_ids: imageIds,
  })
  return response.data
}

export async function getAssetImageThumbnail(imageId) {
  const response = await axios.get(`/api/assets/files/thumbnail/${imageId}`, {
    responseType: 'blob',
  })
  return URL.createObjectURL(response.data)
}

export async function getAssetImageOriginal(imageId) {
  const response = await axios.get(`/api/assets/files/original/${imageId}`, {
    responseType: 'blob',
  })
  return URL.createObjectURL(response.data)
}

export function originalUrl(imageId) {
  return `/api/assets/files/original/${imageId}`
}

export async function getAssetTags() {
  const response = await axios.get('/api/assets/tags')
  return response.data.tags
}

export async function getAssetCategories() {
  const response = await axios.get('/api/assets/categories')
  return response.data.categories
}
