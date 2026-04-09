import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { jwtDecode } from 'jwt-decode'
import api from '@/lib/api'

interface User {
  email: string
  name: string
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
}

interface AuthContextValue extends AuthState {
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

// eslint-disable-next-line react-refresh/only-export-components
const AuthContext = createContext<AuthContextValue | null>(null)

function isTokenValid(token: string): boolean {
  try {
    const { exp } = jwtDecode<{ exp: number }>(token)
    return exp * 1000 > Date.now()
  } catch {
    return false
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true, // inicia true para evitar flash da tela de login
  })

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token && isTokenValid(token)) {
      try {
        const payload = jwtDecode<{ email?: string; username?: string; name?: string }>(token)
        const email = payload.email ?? payload.username ?? ''
        setState({
          user: { email, name: payload.name ?? email ?? 'Admin' },
          isAuthenticated: true,
          isLoading: false,
        })
      } catch {
        setState({ user: null, isAuthenticated: false, isLoading: false })
      }
    } else {
      setState({ user: null, isAuthenticated: false, isLoading: false })
    }
  }, [])

  async function login(email: string, password: string) {
    // simplejwt espera o campo 'username', nao 'email'
    const { data } = await api.post('/api/auth/token/', { username: email, password })
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    try {
      const payload = jwtDecode<{ email?: string; username?: string; name?: string }>(data.access)
      // Usar email do parametro como fallback pois simplejwt pode nao incluir 'email' no payload
      const resolvedEmail = payload.email ?? payload.username ?? email
      setState({
        user: { email: resolvedEmail, name: payload.name ?? resolvedEmail },
        isAuthenticated: true,
        isLoading: false,
      })
    } catch {
      // Fallback: usar email fornecido no login
      setState({
        user: { email, name: email },
        isAuthenticated: true,
        isLoading: false,
      })
    }
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    setState({ user: null, isAuthenticated: false, isLoading: false })
  }

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider')
  return ctx
}
