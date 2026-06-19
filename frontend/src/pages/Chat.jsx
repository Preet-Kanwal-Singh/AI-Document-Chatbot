import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import api from '../api/axios'
import ReactMarkdown from 'react-markdown'

function Chat() {
  const { documentId } = useParams()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [docName, setDocName] = useState('')
  const bottomRef = useRef()

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await api.get(`/chat/${documentId}/history`)
        setMessages(res.data.messages)
      } catch {
        // No history yet, that's fine
      }

      try {
        const docRes = await api.get(`/documents/${documentId}`)
        setDocName(docRes.data.filename)
      } catch {
        // fallback to document ID
      }
    }

    fetchHistory()
  }, [documentId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const sendMessage = async () => {
  if (!question.trim() || loading) return

  const userMessage = { role: 'user', content: question }
  setMessages(prev => [...prev, userMessage])
  setQuestion('')
  setLoading(true)

  // Add empty assistant message to start filling
  setMessages(prev => [...prev, { role: 'assistant', content: '' }])

  try {
    const response = await fetch('https://ai-document-chatbot-oqd9.onrender.com/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        document_id: parseInt(documentId),
        question: userMessage.content,
      }),
    })

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      const chunk = decoder.decode(value)
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          ...updated[updated.length - 1],
          content: updated[updated.length - 1].content + chunk
      }
      return updated
      })
    await new Promise(resolve => setTimeout(resolve, 30)) // adjust ms to taste
}
  } catch {
    setMessages(prev => {
      const updated = [...prev]
      updated[updated.length - 1] = {
        ...updated[updated.length - 1],
        content: 'Something went wrong. Please try again.'
      }
      return updated
    })
  } finally {
    setLoading(false)
  }
}

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      maxWidth: '800px',
      margin: '0 auto',
    }}>
      {/* Header */}
      <div style={{
        padding: '1rem 1.5rem',
        borderBottom: '1px solid #1e2130',
        display: 'flex',
        alignItems: 'center',
        gap: '1rem',
        backgroundColor: '#0f1117',
      }}>
        <button
          onClick={() => navigate('/')}
          style={{
            background: 'none',
            border: '1px solid #333',
            color: '#888',
            padding: '0.4rem 0.8rem',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.85rem',
          }}
        >
          ← New Document
        </button>
        <span style={{ color: '#888', fontSize: '0.9rem' }}>
          {docName || `Document #${documentId}`}
        </span>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '1.5rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '1rem',
      }}>
        {messages.length === 0 && !loading && (
          <div style={{
            textAlign: 'center',
            color: '#444',
            marginTop: '4rem',
          }}>
            <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>💬</div>
            <p>Ask anything about your document</p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} style={{
            display: 'flex',
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
          }}>
            <div style={{
              maxWidth: '70%',
              padding: '0.75rem 1rem',
              borderRadius: msg.role === 'user'
                ? '18px 18px 4px 18px'
                : '18px 18px 18px 4px',
              backgroundColor: msg.role === 'user' ? '#6366f1' : '#1a1d27',
              color: '#e0e0e0',
              fontSize: '0.95rem',
              lineHeight: '1.5',
              whiteSpace: msg.role === 'user' ? 'pre-wrap' : 'normal',
            }}>
              {msg.role === 'assistant'
                ? <ReactMarkdown>{msg.content}</ReactMarkdown>
                : msg.content
              }
            </div>
          </div>
        ))}
        {loading && messages[messages.length - 1]?.content === '' && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{
              padding: '0.75rem 1rem',
              borderRadius: '18px 18px 18px 4px',
              backgroundColor: '#1a1d27',
              color: '#888',
              fontSize: '1.2rem',
              letterSpacing: '2px',
            }}>
              <span style={{ animation: 'pulse 1s infinite' }}>•••</span>
            </div>
          </div>
        )}
        

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        padding: '1rem 1.5rem',
        borderTop: '1px solid #1e2130',
        display: 'flex',
        gap: '0.75rem',
        backgroundColor: '#0f1117',
      }}>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question about your document..."
          rows={1}
          style={{
            flex: 1,
            padding: '0.75rem 1rem',
            backgroundColor: '#1a1d27',
            border: '1px solid #2a2d3e',
            borderRadius: '10px',
            color: '#e0e0e0',
            fontSize: '0.95rem',
            resize: 'none',
            outline: 'none',
            fontFamily: 'inherit',
          }}
        />
        <button
          onClick={sendMessage}
          disabled={loading || !question.trim()}
          style={{
            padding: '0.75rem 1.25rem',
            backgroundColor: loading || !question.trim() ? '#333' : '#6366f1',
            color: 'white',
            border: 'none',
            borderRadius: '10px',
            cursor: loading || !question.trim() ? 'not-allowed' : 'pointer',
            fontSize: '1rem',
            transition: 'background-color 0.2s',
          }}
        >
          ➤
        </button>
      </div>
    </div>
  )
}

export default Chat
