import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'
import { jwtDecode } from 'jwt-decode'
import api from '@/lib/api'

interface User {
  email: string
  name: string
  is_staff: boolean
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

// Cookie usado pelo nginx para validar acesso ao Grafana (auth_request).
// Path=/grafana limita o envio apenas para requests ao Grafana.
function setGrafanaCookie(token: string) {
  const maxAge = 12 * 3600 // mesma duração do access token
  document.cookie = `fs_access_token=${token}; path=/grafana; secure; samesite=strict; max-age=${maxAge}`
}

function clearGrafanaCookie() {
  document.cookie = 'fs_access_token=; path=/grafana; max-age=0'
}

function isTokenValid(token: string): boolean {
  try {
    const { exp } = jwtDecode<{ exp: number }>(token)
    return exp * 1000 > Date.now()
  } catch {
    return false
  }
}

interface MeResponse {
  id: number
  email: string
  username: string
  name: string
  is_staff: boolean
}

async function buscarPerfil(): Promise<User | null> {
  try {
    const { data } = await api.get<MeResponse>('/api/auth/me/')
    return {
      email: data.email || data.username,
      name: data.name || data.email || data.username,
      is_staff: !!data.is_staff,
    }
  } catch {
    return null
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
    if (!token || !isTokenValid(token)) {
      clearGrafanaCookie()
      setState({ user: null, isAuthenticated: false, isLoading: false })
      return
    }
    setGrafanaCookie(token)

    // Token válido — marca como autenticado e busca perfil em paralelo.
    // Perfil vem do backend para ter email/nome/is_staff confiáveis.
    setState({ user: null, isAuthenticated: true, isLoading: true })
    void buscarPerfil().then((user) => {
      if (user) {
        setState({ user, isAuthenticated: true, isLoading: false })
      } else {
        // Falha ao buscar perfil mas token parecia válido — logout defensivo.
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        setState({ user: null, isAuthenticated: false, isLoading: false })
      }
    })
  }, [])

  async function login(email: string, password: string) {
    // simplejwt espera o campo 'username', nao 'email'
    const { data } = await api.post('/api/auth/token/', { username: email, password })
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    setGrafanaCookie(data.access)

    const user = await buscarPerfil()
    setState({
      user: user ?? { email, name: email, is_staff: false },
      isAuthenticated: true,
      isLoading: false,
    })
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    clearGrafanaCookie()
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
