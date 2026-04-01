import type { ColumnDef } from "@tanstack/react-table"

import type { ServiceAccountPublic } from "@/client"
import { cn } from "@/lib/utils"
import { ServiceAccountActionsMenu } from "./ActionsMenu"

export type ServiceAccountTableData = ServiceAccountPublic

export const columns: ColumnDef<ServiceAccountTableData>[] = [
  {
    accessorKey: "display_name",
    header: "Name",
    cell: ({ row }) => (
      <span className="font-medium">{row.original.display_name}</span>
    ),
  },
  {
    accessorKey: "description",
    header: "Description",
    cell: ({ row }) => (
      <span
        className={cn(!row.original.description && "text-muted-foreground")}
      >
        {row.original.description || "N/A"}
      </span>
    ),
  },
  {
    accessorKey: "user_id",
    header: "Assigned User",
    cell: ({ row }) => (
      <span className="text-muted-foreground text-xs">
        {row.original.user_id}
      </span>
    ),
  },
  {
    id: "actions",
    header: () => <span className="sr-only">Actions</span>,
    cell: ({ row }) => (
      <div className="flex justify-end">
        <ServiceAccountActionsMenu serviceAccount={row.original} />
      </div>
    ),
  },
]
