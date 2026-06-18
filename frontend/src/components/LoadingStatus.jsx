const steps = [
  'Uploading document',
  'Extracting text',
  'Generating embeddings',
  'Saving data',
  'Preparing chatbot',
]

function LoadingStatus({ currentStep }) {
  return (
    <div style={{ marginTop: '2rem', width: '100%', maxWidth: '400px' }}>
      {steps.map((step, index) => {
        const isDone = index < currentStep
        const isActive = index === currentStep

        return (
          <div key={step} style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '0.6rem 0',
            opacity: isDone || isActive ? 1 : 0.3,
          }}>
            <div style={{
              width: '20px',
              height: '20px',
              borderRadius: '50%',
              backgroundColor: isDone ? '#4ade80' : isActive ? '#6366f1' : '#333',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '12px',
              flexShrink: 0,
              animation: isActive ? 'pulse 1s infinite' : 'none',
            }}>
              {isDone ? '✓' : ''}
            </div>
            <span style={{
              fontSize: '0.9rem',
              color: isDone ? '#4ade80' : isActive ? '#a5b4fc' : '#666',
            }}>
              {step}
            </span>
          </div>
        )
      })}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </div>
  )
}

export default LoadingStatus