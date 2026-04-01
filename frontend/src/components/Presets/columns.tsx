import type { ColumnDef } from "@tanstack/react-table"

import type { ConventionPresetPublic } from "@/client"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { PresetActionsMenu } from "./ActionsMenu"

export const columns: ColumnDef<ConventionPresetPublic>[] = [
  {
    accessorKey: "name",
    header: "Name",
    cell: ({ row }) => <span className="font-medium">{row.original.name}</span>,
  },
  {
    accessorKey: "convention",
    header: "Convention",
    cell: ({ row }) => (
      <code className="bg-muted rounded px-1.5 py-0.5 text-xs">
        {row.original.convention}
      </code>
    ),
  },
  {
    accessorKey: "content_type",
    header: "Content Type",
    cell: ({ row }) => {
      const ct = row.original.content_type
      return ct ? (
        <Badge variant="secondary">{ct}</Badge>
      ) : (
        <span className="text-muted-foreground">—</span>
      )
    },
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => (
      <span
        className={cn(
          "text-sm",
          !row.original.description && "text-muted-foreground",
        )}
      >
        {row.original.description || "—"}
      </span>
    ),
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <PresetActionsMenu preset={row.original} />
      </div>
    ),
  },
]
