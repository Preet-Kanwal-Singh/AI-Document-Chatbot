import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Upload from './pages/Upload'
import Chat from './pages/Chat'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Upload />} />
        <Route path="/chat/:documentId" element={<Chat />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App