import axios from 'axios'

export async function createQualityJob(batchId) {
  const response = await axios.post(`/api/assets/imports/${batchId}/quality/jobs`)
  return response.data
}

export async function getQualityJob(jobId) {
  const response = await axios.get(`/api/assets/quality/jobs/${jobId}`)
  return response.data
}

export async function getQualityMetrics(batchId, profileKey) {
  const response = await axios.get(`/api/assets/imports/${batchId}/quality/metrics`, {
    params: { profile_key: profileKey || undefined },
  })
  return response.data
}

export async function getQualityHistograms(batchId, profileKey) {
  const response = await axios.get(`/api/assets/imports/${batchId}/quality/histograms`, {
    params: { profile_key: profileKey || undefined },
  })
  return response.data
}

export async function evaluateQualityPreview(batchId, payload) {
  const response = await axios.post(
    `/api/assets/imports/${batchId}/quality/evaluate-preview`,
    payload,
  )
  return response.data
}

export async function getQualityCandidates(batchId, params) {
  const response = await axios.get(`/api/assets/imports/${batchId}/quality/candidates`, {
    params,
  })
  return response.data
}

export async function getQualityProfiles() {
  const response = await axios.get('/api/assets/quality/profiles')
  return response.data
}

export async function updateQualityProfile(profileId, config) {
  const response = await axios.put(`/api/assets/quality/profiles/${profileId}`, { config })
  return response.data
}

export async function createQualityEvaluation(batchId, payload) {
  const response = await axios.post(
    `/api/assets/imports/${batchId}/quality/evaluations`,
    payload,
  )
  return response.data
}

export async function createQualityExport(evaluationId) {
  const response = await axios.post(
    `/api/assets/quality/evaluations/${evaluationId}/exports`,
  )
  return response.data
}

export async function getQualityExport(exportId) {
  const response = await axios.get(`/api/assets/quality/exports/${exportId}`)
  return response.data
}

export async function downloadQualityExport(exportId) {
  const response = await axios.get(
    `/api/assets/quality/exports/${exportId}/download`,
    { responseType: 'blob' },
  )
  return response
}

export async function createQualityReview(payload) {
  const response = await axios.post('/api/assets/quality/reviews', payload)
  return response.data
}

export async function getQualityCandidateImage(candidateId, size = 320) {
  const response = await axios.get(
    `/api/assets/quality/candidates/${candidateId}/thumbnail`,
    { params: { size }, responseType: 'blob' },
  )
  return URL.createObjectURL(response.data)
}
