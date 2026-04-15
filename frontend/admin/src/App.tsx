import { createBrowserRouter, RouterProvider, Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '@/contexts/auth'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { UsinasPage } from '@/pages/UsinasPage'
import { UsinaDetalhePage } from '@/pages/UsinaDetalhePage'
import { GarantiasPage } from '@/pages/GarantiasPage'
import { AlertasPage } from '@/pages/AlertasPage'
import { AlertaDetalhePage } from '@/pages/AlertaDetalhePage'
import { ConfiguracoesPage } from '@/pages/ConfiguracoesPage'
import { ProvedoresPage } from '@/pages/ProvedoresPage'
import { NotificacoesPage } from '@/pages/NotificacoesPage'
import { NotificationBell } from '@/components/notificacoes/NotificationBell'
import { Toaster } from '@/components/ui/sonner'
import { AppSidebar } from '@/components/app-sidebar'
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbPage,
} from '@/components/ui/breadcrumb'
import { Loader2Icon } from 'lucide-react'

const ROUTE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/dashboard': 'Dashboard',
  '/usinas': 'Usinas',
  '/garantias': 'Garantias',
  '/alertas': 'Alertas',
  '/configuracoes': 'Configurações',
  '/provedores': 'Provedores',
  '/notificacoes': 'Notificações',
}

function ProtectedLayout() {
  const { isAuthenticated, isLoading } = useAuth()
  const { pathname } = useLocation()
  const pageTitle = ROUTE_TITLES[pathname] ?? 'Firma Solar'

  if (isLoading) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <Loader2Icon className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <header className="flex h-14 shrink-0 items-center gap-2 border-b px-4">
          <SidebarTrigger className="-ml-1" />
          <Separator orientation="vertical" className="mr-2 h-4" />
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbPage>{pageTitle}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <div className="ml-auto">
            <NotificationBell />
          </div>
        </header>
        <main className="flex-1 p-4">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}

const router = createBrowserRouter([
  { path: '/login', element: <LoginPage /> },
  {
    element: <ProtectedLayout />,
    children: [
      { index: true, element: <DashboardPage /> },
      { path: 'dashboard', element: <DashboardPage /> },
      { path: 'usinas/:id', element: <UsinaDetalhePage /> },
      { path: 'usinas', element: <UsinasPage /> },
      { path: 'garantias', element: <GarantiasPage /> },
      { path: 'alertas/:id', element: <AlertaDetalhePage /> },
      { path: 'alertas', element: <AlertasPage /> },
      { path: 'configuracoes', element: <ConfiguracoesPage /> },
      { path: 'provedores', element: <ProvedoresPage /> },
      { path: 'notificacoes', element: <NotificacoesPage /> },
    ],
  },
])

export default function App() {
  return (
    <>
      <RouterProvider router={router} />
      <Toaster />
    </>
  )
}
