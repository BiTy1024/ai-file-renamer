import { useQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"

import { type UserPublic, UsersService } from "@/client"
import { SetLimitsDialog } from "@/components/Usage/SetLimitsDialog"
import { UsageBar } from "@/components/Usage/UsageBar"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

export const Route = createFileRoute("/_layout/usage")({
  component: UsagePage,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (user.role !== "admin") {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Usage - AI-Namer" }],
  }),
})

function UserUsageRow({ user }: { user: UserPublic }) {
  const { data: usage, isLoading } = useQuery({
    queryKey: ["user-usage", user.id],
    queryFn: () => UsersService.readUserUsage({ userId: user.id }),
  })

  return (
    <TableRow>
      <TableCell>
        <div>
          <span className="font-medium">{user.email}</span>
        </div>
      </TableCell>
      <TableCell>
        <Badge variant="secondary">
          {(user.role ?? "viewer").charAt(0).toUpperCase() +
            (user.role ?? "viewer").slice(1)}
        </Badge>
      </TableCell>
      <TableCell>
        {isLoading ? (
          <Skeleton className="h-6 w-20" />
        ) : (
          <UsageBar
            current={usage?.requests_today ?? 0}
            limit={usage?.limit?.max_requests_per_day ?? null}
            label="req/day"
          />
        )}
      </TableCell>
      <TableCell>
        {isLoading ? (
          <Skeleton className="h-6 w-20" />
        ) : (
          <UsageBar
            current={usage?.tokens_this_month ?? 0}
            limit={usage?.limit?.max_tokens_per_month ?? null}
            label="tokens/mo"
          />
        )}
      </TableCell>
      <TableCell>
        <SetLimitsDialog
          userId={user.id}
          userEmail={user.email}
          currentRequestsPerDay={usage?.limit?.max_requests_per_day ?? null}
          currentTokensPerMonth={usage?.limit?.max_tokens_per_month ?? null}
        />
      </TableCell>
    </TableRow>
  )
}

function UsagePage() {
  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => UsersService.readUsers({ skip: 0, limit: 100 }),
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Usage & Limits</h1>
        <p className="text-muted-foreground">
          Monitor API usage and manage rate limits per user
        </p>
      </div>

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={`skeleton-${i}`} className="h-14 rounded" />
          ))}
        </div>
      )}

      {users && (
        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Requests Today</TableHead>
                <TableHead>Tokens This Month</TableHead>
                <TableHead className="w-12">Limits</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.data.map((user) => (
                <UserUsageRow key={user.id} user={user} />
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
