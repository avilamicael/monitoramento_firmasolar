import { NavLink, useLocation } from 'react-router'
import { ChevronRightIcon, ExternalLinkIcon, type LucideIcon } from 'lucide-react'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSub,
  SidebarMenuSubButton,
  SidebarMenuSubItem,
} from '@/components/ui/sidebar'

export interface NavGroup {
  label: string
  icon: LucideIcon
  items: {
    title: string
    url: string
    external?: boolean
  }[]
}

function isGroupActive(group: NavGroup, pathname: string): boolean {
  return group.items.some((item) => {
    if (item.url === '/') return pathname === '/'
    return pathname === item.url || pathname.startsWith(item.url + '/')
  })
}

export function NavMain({ groups }: { groups: NavGroup[] }) {
  const { pathname } = useLocation()

  return (
    <SidebarGroup>
      <SidebarGroupLabel>Plataforma</SidebarGroupLabel>
      <SidebarMenu>
        {groups.map((group) => (
          <Collapsible
            key={group.label}
            asChild
            defaultOpen={isGroupActive(group, pathname)}
            className="group/collapsible"
          >
            <SidebarMenuItem>
              <CollapsibleTrigger asChild>
                <SidebarMenuButton tooltip={group.label}>
                  <group.icon />
                  <span>{group.label}</span>
                  <ChevronRightIcon className="ml-auto transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                </SidebarMenuButton>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <SidebarMenuSub>
                  {group.items.map((item) => (
                    <SidebarMenuSubItem key={item.title}>
                      <SidebarMenuSubButton asChild>
                        {item.external ? (
                          <a href={item.url} target="_blank" rel="noopener noreferrer">
                            <span>{item.title}</span>
                            <ExternalLinkIcon className="ml-auto size-3 opacity-50" />
                          </a>
                        ) : (
                          <NavLink to={item.url} end={item.url === '/'}>
                            <span>{item.title}</span>
                          </NavLink>
                        )}
                      </SidebarMenuSubButton>
                    </SidebarMenuSubItem>
                  ))}
                </SidebarMenuSub>
              </CollapsibleContent>
            </SidebarMenuItem>
          </Collapsible>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  )
}
