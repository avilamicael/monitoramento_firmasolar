import * as React from 'react'
import { LayoutDashboardIcon, ZapIcon, ShieldIcon, BellIcon } from 'lucide-react'

import { NavMain } from '@/components/nav-main'
import { NavUser } from '@/components/nav-user'
import { useAuth } from '@/contexts/auth'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from '@/components/ui/sidebar'

const navItems = [
  { title: 'Dashboard', url: '/', icon: <LayoutDashboardIcon /> },
  { title: 'Usinas', url: '/usinas', icon: <ZapIcon /> },
  { title: 'Garantias', url: '/garantias', icon: <ShieldIcon /> },
  { title: 'Alertas', url: '/alertas', icon: <BellIcon /> },
]

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { user } = useAuth()

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <div className="flex items-center gap-2 px-2 py-1">
          <ZapIcon className="size-5 text-yellow-500" />
          <span className="font-semibold text-sm">Firma Solar</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={navItems} />
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
