import { useQueryClient } from "@tanstack/react-query"
import { MoreHorizontal } from "lucide-react"

import type { ConventionPresetPublic } from "@/client"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import DeletePreset from "./DeletePreset"
import EditPreset from "./EditPreset"

interface PresetActionsMenuProps {
  preset: ConventionPresetPublic
}

export function PresetActionsMenu({ preset }: PresetActionsMenuProps) {
  const queryClient = useQueryClient()

  const handleSuccess = () => {
    queryClient.invalidateQueries({ queryKey: ["presets"] })
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
        <EditPreset preset={preset} onSuccess={handleSuccess} />
        <DeletePreset preset={preset} onSuccess={handleSuccess} />
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
