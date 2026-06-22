import { useState } from 'react'
import api from '../api/axios'
import { AuthContext } from './auth-context'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'))
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('user')
    return stored ? JSON.parse(stored) : null
  })

  const login = async (email, password) => {
    const res = await api.post('/auth/login', { email, password })
    const newToken = res.data.access_token
    const userInfo = { email }

    localStorage.setItem('token', newToken)
    localStorage.setItem('user', JSON.stringify(userInfo))
    setToken(newToken)
    setUser(userInfo)
  }

  const signup = async (email, password) => {
    await api.post('/auth/signup', { email, password })
    // Backend doesn't auto-login on signup, so log in right after creating the account
    await login(email, password)
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{ token, user, login, signup, logout, isAuthenticated: !!token }}
    >
      {children}
    </AuthContext.Provider>
  )
}
