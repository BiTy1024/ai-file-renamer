import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link, redirect } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"

import { AdminService, UsersService } from "@/client"
import { SetLimitsDialog } from "@/components/Usage/SetLimitsDialog"
import { UsageBar } from "@/components/Usage/UsageBar"
import { UsageChart } from "@/components/Usage/UsageChart"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export const Route = createFileRoute("/_layout/usage/$userId")({
  component: UserDetailPage,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (user.role !== "admin") {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "User Detail - AI-Namer" }],
  }),
})

function UserDetailPage() {
  const { userId } = Route.useParams()

  const { data: user, isLoading: userLoading } = useQuery({
    queryKey: ["user", userId],
    queryFn: () => UsersService.readUserById({ userId }),
  })

  const { data: usage, isLoading: usageLoading } = useQuery({
    queryKey: ["user-usage", userId],
    queryFn: () => UsersService.readUserUsage({ userId }),
  })

  const { data: activity, isLoading: activityLoading } = useQuery({
    queryKey: ["user-activity", userId],
    queryFn: () => AdminService.readUserActivity({ userId, limit: 20 }),
  })

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" asChild>
          <Link to="/usage">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div>
          {userLoading ? (
            <Skeleton className="h-8 w-48" />
          ) : (
            <>
              <h1 className="text-2xl font-bold tracking-tight">
                {user?.full_name || user?.email}
              </h1>
              <div className="text-muted-foreground flex items-center gap-2 text-sm">
                <span>{user?.email}</span>
                <Badge variant="secondary">
                  {(user?.role ?? "viewer").charAt(0).toUpperCase() +
                    (user?.role ?? "viewer").slice(1)}
                </Badge>
              </div>
            </>
          )}
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Current Usage</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {usageLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : (
              <>
                <UsageBar
                  current={usage?.requests_today ?? 0}
                  limit={usage?.limit?.max_requests_per_day ?? null}
                  label="requests / day"
                />
                <UsageBar
                  current={usage?.tokens_this_month ?? 0}
                  limit={usage?.limit?.max_tokens_per_month ?? null}
                  label="tokens / month"
                />
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Rate Limits</CardTitle>
            {user && (
              <SetLimitsDialog
                userId={user.id}
                userEmail={user.email}
                currentRequestsPerDay={
                  usage?.limit?.max_requests_per_day ?? null
                }
                currentTokensPerMonth={
                  usage?.limit?.max_tokens_per_month ?? null
                }
              />
            )}
          </CardHeader>
          <CardContent>
            {usageLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : (
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Requests per day
                  </span>
                  <span className="font-medium">
                    {usage?.limit?.max_requests_per_day ?? "Unlimited"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">
                    Tokens per month
                  </span>
                  <span className="font-medium">
                    {usage?.limit?.max_tokens_per_month?.toLocaleString() ??
                      "Unlimited"}
                  </span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <UsageChart userId={userId} />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Recent Rename Operations</CardTitle>
        </CardHeader>
        <CardContent>
          {activityLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : !activity?.data || activity.data.length === 0 ? (
            <p className="text-muted-foreground text-sm">
              No rename operations yet
            </p>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Original Name</TableHead>
                    <TableHead>New Name</TableHead>
                    <TableHead>Folder</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {activity.data.map((entry) => (
                    <TableRow key={entry.id}>
                      <TableCell className="text-muted-foreground text-xs">
                        {entry.created_at
                          ? new Date(entry.created_at).toLocaleDateString()
                          : "-"}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-sm">
                        {entry.original_name}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate text-sm font-medium">
                        {entry.new_name}
                      </TableCell>
                      <TableCell className="text-muted-foreground max-w-[120px] truncate text-xs">
                        {entry.folder_id}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
