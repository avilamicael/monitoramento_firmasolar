import * as React from 'react'
import {
  ZapIcon,
  ActivityIcon,
  SettingsIcon,
} from 'lucide-react'

import { NavMain, type NavGroup } from '@/components/nav-main'
import { NavUser } from '@/components/nav-user'
import { useAuth } from '@/contexts/auth'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarRail,
} from '@/components/ui/sidebar'

const navGroups: NavGroup[] = [
  {
    label: 'Monitoramento',
    icon: ActivityIcon,
    items: [
      { title: 'Dashboard', url: '/' },
      { title: 'Usinas', url: '/usinas' },
      { title: 'Alertas', url: '/alertas' },
    ],
  },
  {
    label: 'Gestao',
    icon: SettingsIcon,
    items: [
      { title: 'Garantias', url: '/garantias' },
      { title: 'Provedores', url: '/provedores' },
      { title: 'Notificações', url: '/gestao-notificacoes' },
      { title: 'Usuários', url: '/usuarios' },
      { title: 'Configurações', url: '/configuracoes' },
    ],
  },
]

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { user } = useAuth()

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              size="lg"
              className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
            >
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
                <ZapIcon className="size-4" />
              </div>
              <div className="grid flex-1 text-left text-sm leading-tight">
                <span className="truncate font-medium">Firma Solar</span>
                <span className="truncate text-xs">Painel Admin</span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <NavMain groups={navGroups} />
      </SidebarContent>
      <SidebarFooter>
        <NavUser
          user={{
            name: user?.name ?? 'Admin',
            email: user?.email ?? '',
            avatar: '',
          }}
        />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
