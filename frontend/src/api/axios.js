import axios from 'axios'

const api = axios.create({
  baseURL: 'https://ai-document-chatbot-oqd9.onrender.com',
})

export default api