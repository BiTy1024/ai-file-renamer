import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"
import { ArrowRight, History } from "lucide-react"

import { RenameService } from "@/client"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export const Route = createFileRoute("/_layout/rename-history")({
  component: RenameHistoryPage,
  head: () => ({
    meta: [{ title: "Rename History - AI-Namer" }],
  }),
})

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "-"
  return new Date(dateStr).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

function RenameHistoryPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["rename-history"],
    queryFn: () => RenameService.readRenameHistory({ skip: 0, limit: 100 }),
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Rename History</h1>
        <p className="text-muted-foreground">
          Track all file renames performed through AI-Namer
        </p>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={`skeleton-${i}`} className="h-12 rounded" />
          ))}
        </div>
      )}

      {error && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">Failed to load history</p>
          </CardContent>
        </Card>
      )}

      {data && !data.data?.length && (
        <Card>
          <CardContent className="py-8 text-center">
            <History className="text-muted-foreground mx-auto mb-3 size-10" />
            <p className="text-muted-foreground">No renames yet.</p>
          </CardContent>
        </Card>
      )}

      {data && data.data?.length > 0 && (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Original Name</TableHead>
                <TableHead className="w-8" />
                <TableHead>New Name</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.data.map((log) => (
                <TableRow key={log.id}>
                  <TableCell className="text-muted-foreground text-sm">
                    {formatDate(log.created_at)}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {log.original_name}
                  </TableCell>
                  <TableCell>
                    <ArrowRight className="text-muted-foreground size-4" />
                  </TableCell>
                  <TableCell className="text-sm font-medium">
                    {log.new_name}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {data && (
        <p className="text-muted-foreground text-sm">
          {data.count} rename{data.count !== 1 ? "s" : ""} total
        </p>
      )}
    </div>
  )
}
