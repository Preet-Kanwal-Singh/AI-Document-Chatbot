import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/axios'
import LoadingStatus from '../components/LoadingStatus'
import { useAuth } from '../context/auth-context'

const STEP_DELAYS = [0, 1000, 2500, 4000, 5000]

const VIDEO_MIME_TYPES = [
  'video/mp4', 'video/mpeg', 'video/quicktime', 'video/avi',
  'video/x-flv', 'video/mpg', 'video/webm', 'video/wmv', 'video/3gpp',
]

const POLL_INTERVAL_MS = 3000
const POLL_TIMEOUT_MS = 10 * 60 * 1000 // 10 minutes

function Upload() {
  const { logout } = useAuth()
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [recentDocs, setRecentDocs] = useState([])
  const [currentStep, setCurrentStep] = useState(0)
  const [error, setError] = useState('')
  const fileInputRef = useRef()
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/documents/')
      .then(res => setRecentDocs(res.data))
      .catch(() => {})
  }, [])

  const handleUpload = async () => {
    if (!file) return
    setError('')
    setUploading(true)
    setCurrentStep(0)

    // Start cycling through status steps
    STEP_DELAYS.forEach((delay, index) => {
      setTimeout(() => setCurrentStep(index), delay)
    })

    try {
      const formData = new FormData()
      formData.append('file', file)

      const isVideo = VIDEO_MIME_TYPES.includes(file.type)
      const endpoint = isVideo ? '/documents/upload-video' : '/documents/upload'

      const response = await api.post(endpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })

      if (isVideo) {
        // Video processing is async (202) — poll until ready
        const docId = response.data.id
        const start = Date.now()
        while (Date.now() - start < POLL_TIMEOUT_MS) {
          await new Promise(r => setTimeout(r, POLL_INTERVAL_MS))
          const statusRes = await api.get(`/documents/${docId}`)
          const status = statusRes.data.status
          if (status === 'ready') break
          if (status === 'failed') {
            throw new Error(statusRes.data.error_message || 'Video processing failed')
          }
        }
      }

      setCurrentStep(5) // all done
      setTimeout(() => navigate(`/chat/${response.data.id}`), 800)
    } catch (err) {
      setError(err.message || 'Upload failed. Please try again.')
      setUploading(false)
    }
  }

  const handleDelete = async (e, docId) => {
    e.stopPropagation()
    try {
      await api.delete(`/documents/${docId}`)
      setRecentDocs(prev => prev.filter(d => d.id !== docId))
    } catch {
      setError('Failed to delete document. Please try again.')
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      position: 'relative',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
    }}>
      <button
        onClick={logout}
        style={{
          position: 'absolute',
          top: '1.5rem',
          right: '1.5rem',
          background: 'none',
          border: '1px solid #333',
          color: '#888',
          padding: '0.4rem 0.8rem',
          borderRadius: '6px',
          cursor: 'pointer',
          fontSize: '0.85rem',
        }}
      >
        Logout
      </button>
      <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
        AI Document Chatbot
      </h1>
      <p style={{ color: '#888', marginBottom: '2rem' }}>
        Upload a document to start chatting with it
      </p>

      {!uploading ? (
        <div style={{
          border: '2px dashed #333',
          borderRadius: '12px',
          padding: '3rem',
          textAlign: 'center',
          width: '100%',
          maxWidth: '400px',
          cursor: 'pointer',
          backgroundColor: '#1a1d27',
        }}
          onClick={() => fileInputRef.current.click()}
        >
          <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📄</div>
          <p style={{ color: '#888', marginBottom: '1rem' }}>
            {file ? file.name : 'Click to select a document (PDF, DOCX, TXT), audio (MP3, WAV, M4A), or video (MP4, MOV, AVI)'}
          </p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt,.mp3,.wav,.m4a,.ogg,.webm,.flac,.mp4,.mov,.avi,.wmv,.flv,.3gp,.mpg,.mpeg"
            style={{ display: 'none' }}
            onChange={(e) => setFile(e.target.files[0])}
          />
          {file && (
            <button
              onClick={(e) => { e.stopPropagation(); handleUpload() }}
              style={{
                marginTop: '1rem',
                padding: '0.75rem 2rem',
                backgroundColor: '#6366f1',
                color: 'white',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '1rem',
              }}
            >
              Upload & Process
            </button>
          )}
        </div>
      ) : (
        <div style={{
          backgroundColor: '#1a1d27',
          borderRadius: '12px',
          padding: '2rem',
          width: '100%',
          maxWidth: '400px',
          textAlign: 'center',
        }}>
          <p style={{ marginBottom: '1rem', color: '#a5b4fc' }}>
            Processing <strong>{file.name}</strong>
          </p>
          <LoadingStatus currentStep={currentStep} />
        </div>
      )}

      {error && <p style={{ color: '#f87171', marginTop: '1rem' }}>{error}</p>}

      {/* Recent Documents Section */}
      {recentDocs.length > 0 && (
        <div style={{ marginTop: '2rem', width: '100%', maxWidth: '400px' }}>
          <p style={{ color: '#666', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
            Recent Documents
          </p>
          {recentDocs.map(doc => (
            <div
              key={doc.id}
              onClick={() => navigate(`/chat/${doc.id}`)}
              style={{
                padding: '0.75rem 1rem',
                backgroundColor: '#1a1d27',
                borderRadius: '8px',
                marginBottom: '0.5rem',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                border: '1px solid #2a2d3e',
              }}
            >
              <span style={{ fontSize: '0.9rem', color: '#fff' }}>📄 {doc.filename}</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <span style={{ color: '#666', fontSize: '0.75rem' }}>
                  {new Date(doc.uploaded_at).toLocaleDateString()}
                </span>
                <button
                  onClick={(e) => handleDelete(e, doc.id)}
                  style={{
                    background: 'none',
                    border: '1px solid #444',
                    color: '#888',
                    borderRadius: '4px',
                    padding: '0.2rem 0.5rem',
                    cursor: 'pointer',
                    fontSize: '0.8rem',
                    lineHeight: 1,
                  }}
                  title="Delete document"
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
export default Upload
