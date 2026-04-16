export interface Usuario {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  is_staff: boolean
  is_active: boolean
  is_superuser: boolean
  last_login: string | null
  date_joined: string
}

export interface UsuarioWrite {
  username: string
  email: string
  first_name: string
  last_name: string
  is_staff: boolean
  is_active: boolean
  password?: string
}
