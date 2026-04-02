import {
  BarChart3,
  FolderOpen,
  History,
  Home,
  KeyRound,
  ListChecks,
  Users,
} from "lucide-react"

import { SidebarAppearance } from "@/components/Common/Appearance"
import { Logo } from "@/components/Common/Logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"
import useAuth from "@/hooks/useAuth"
import { type Item, Main } from "./Main"
import { User } from "./User"

const baseItems: Item[] = [
  { icon: Home, title: "Dashboard", path: "/" },
  { icon: FolderOpen, title: "Drive", path: "/drive" },
  { icon: History, title: "History", path: "/rename-history" },
]

export function AppSidebar() {
  const { user: currentUser } = useAuth()

  const items =
    currentUser?.role === "admin"
      ? [
          ...baseItems,
          { icon: Users, title: "Admin", path: "/admin" },
          {
            icon: KeyRound,
            title: "Service Accounts",
            path: "/service-accounts",
          },
          { icon: ListChecks, title: "Presets", path: "/presets" },
          { icon: BarChart3, title: "Usage", path: "/usage" },
        ]
      : baseItems

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="px-4 py-6 group-data-[collapsible=icon]:px-0 group-data-[collapsible=icon]:items-center">
        <Logo variant="responsive" />
      </SidebarHeader>
      <SidebarContent>
        <Main items={items} />
      </SidebarContent>
      <SidebarFooter>
        <SidebarAppearance />
        <User user={currentUser} />
      </SidebarFooter>
    </Sidebar>
  )
}

export default AppSidebar
