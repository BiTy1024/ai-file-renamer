import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Download } from "lucide-react"
import { useState } from "react"

import { type ActivityAction, AdminService, UsersService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export const Route = createFileRoute("/_layout/activity")({
  component: ActivityPage,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (user.role !== "admin") {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Activity Log - AI-Namer" }],
  }),
})

const ACTION_LABELS: Record<ActivityAction, string> = {
  login: "Login",
  logout: "Logout",
  rename: "Rename",
  settings_change: "Settings",
  user_created: "User Created",
  user_deleted: "User Deleted",
  limit_changed: "Limit Changed",
  api_key_changed: "API Key",
}

const ACTION_VARIANTS: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  login: "default",
  logout: "outline",
  rename: "secondary",
  settings_change: "outline",
  user_created: "default",
  user_deleted: "destructive",
  limit_changed: "outline",
  api_key_changed: "outline",
}

function ActivityPage() {
  const [page, setPage] = useState(0)
  const [selectedUser, setSelectedUser] = useState<string>("all")
  const [selectedAction, setSelectedAction] = useState<string>("all")
  const pageSize = 25

  const { data: users } = useQuery({
    queryKey: ["users"],
    queryFn: () => UsersService.readUsers({ skip: 0, limit: 100 }),
  })

  const { data, isLoading } = useQuery({
    queryKey: ["admin-activity", page, selectedUser, selectedAction],
    queryFn: () =>
      AdminService.readActivityLog({
        skip: page * pageSize,
        limit: pageSize,
        userId: selectedUser !== "all" ? selectedUser : undefined,
        action:
          selectedAction !== "all"
            ? (selectedAction as ActivityAction)
            : undefined,
      }),
  })

  const handleExport = async () => {
    const params = new URLSearchParams()
    if (selectedUser !== "all") params.set("user_id", selectedUser)
    const url = `/api/v1/admin/activity/export?${params.toString()}`
    const res = await fetch(url, { credentials: "include" })
    const blob = await res.blob()
    const downloadUrl = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = downloadUrl
    a.download = "activity_log.csv"
    a.click()
    URL.revokeObjectURL(downloadUrl)
  }

  const totalPages = Math.ceil((data?.count ?? 0) / pageSize)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Activity Log</h1>
          <p className="text-muted-foreground">
            Track all user actions across the platform
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleExport}>
          <Download className="mr-2 h-4 w-4" />
          Export CSV
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center gap-3">
            <CardTitle className="text-sm font-medium">Filters</CardTitle>
            <Select
              value={selectedUser}
              onValueChange={(v) => {
                setSelectedUser(v)
                setPage(0)
              }}
            >
              <SelectTrigger className="h-8 w-48">
                <SelectValue placeholder="All users" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All users</SelectItem>
                {users?.data.map((u) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.email}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select
              value={selectedAction}
              onValueChange={(v) => {
                setSelectedAction(v)
                setPage(0)
              }}
            >
              <SelectTrigger className="h-8 w-40">
                <SelectValue placeholder="All actions" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All actions</SelectItem>
                {Object.entries(ACTION_LABELS).map(([key, label]) => (
                  <SelectItem key={key} value={key}>
                    {label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={`skel-${i}`} className="h-12 rounded" />
              ))}
            </div>
          ) : !data?.data || data.data.length === 0 ? (
            <p className="text-muted-foreground py-8 text-center text-sm">
              No activity found
            </p>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Time</TableHead>
                      <TableHead>User</TableHead>
                      <TableHead>Action</TableHead>
                      <TableHead>Detail</TableHead>
                      <TableHead className="text-right">Tokens</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.data.map((entry) => (
                      <TableRow key={entry.id}>
                        <TableCell className="text-muted-foreground text-xs whitespace-nowrap">
                          {entry.created_at
                            ? new Date(entry.created_at).toLocaleString()
                            : "-"}
                        </TableCell>
                        <TableCell className="text-sm">
                          {entry.user_email ?? "-"}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant={ACTION_VARIANTS[entry.action] ?? "outline"}
                          >
                            {ACTION_LABELS[entry.action] ?? entry.action}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground max-w-[300px] truncate text-xs">
                          {entry.detail ?? "-"}
                        </TableCell>
                        <TableCell className="text-right text-sm">
                          {entry.tokens_used?.toLocaleString() ?? "-"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="mt-4 flex items-center justify-between">
                <p className="text-muted-foreground text-xs">
                  {data.count} total entries
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page === 0}
                    onClick={() => setPage((p) => p - 1)}
                  >
                    Previous
                  </Button>
                  <span className="text-muted-foreground text-xs">
                    Page {page + 1} of {totalPages || 1}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={page + 1 >= totalPages}
                    onClick={() => setPage((p) => p + 1)}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
