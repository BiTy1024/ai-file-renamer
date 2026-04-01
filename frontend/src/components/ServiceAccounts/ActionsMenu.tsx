import { useQueryClient } from "@tanstack/react-query"
import { MoreHorizontal } from "lucide-react"

import type { ServiceAccountPublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import DeleteServiceAccount from "./DeleteServiceAccount"
import EditServiceAccount from "./EditServiceAccount"

interface ServiceAccountActionsMenuProps {
  serviceAccount: ServiceAccountPublic
}

export function ServiceAccountActionsMenu({
  serviceAccount,
}: ServiceAccountActionsMenuProps) {
  const queryClient = useQueryClient()

  const handleSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ["service-accounts"] })
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" className="size-8 p-0">
          <span className="sr-only">Open menu</span>
          <MoreHorizontal className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <EditServiceAccount
          serviceAccount={serviceAccount}
          onSuccess={handleSuccess}
        />
        <DeleteServiceAccount
          serviceAccount={serviceAccount}
          onSuccess={handleSuccess}
        />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
