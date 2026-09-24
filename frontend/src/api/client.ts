import axios from 'axios'

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export const getHealth = () => apiClient.get('/health')
export const getSensors = () => apiClient.get('/api/sensors')
export const getSummary = () => apiClient.get('/api/summary')
export const getCertificates = () => apiClient.get('/api/events/certify')
