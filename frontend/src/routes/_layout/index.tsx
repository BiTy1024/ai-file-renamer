import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { ServiceAccountsService, UsersService } from "@/client"
import { UsageBar } from "@/components/Usage/UsageBar"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/")({
  component: Dashboard,
  head: () => ({
    meta: [
      {
        title: "Dashboard - AI-Namer",
      },
    ],
  }),
})

function ServiceAccountInfo() {
  const { data: sa, isLoading } = useQuery({
    queryKey: ["my-service-account"],
    queryFn: () => ServiceAccountsService.readOwnServiceAccount(),
    retry: false,
  })

  if (isLoading) {
    return null
  }

  if (!sa) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Service Account</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">
            No service account assigned. Contact your admin to get access.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Service Account</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <div>
          <span className="text-muted-foreground text-sm">Name: </span>
          <span className="text-sm font-medium">{sa.display_name}</span>
        </div>
        {sa.client_email && (
          <div>
            <span className="text-muted-foreground text-sm">
              Share folders with:{" "}
            </span>
            <code className="bg-muted rounded px-1 py-0.5 text-xs">
              {sa.client_email}
            </code>
          </div>
        )}
        {sa.description && (
          <div>
            <span className="text-muted-foreground text-sm">
              {sa.description}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function MyUsageInfo() {
  const { data: usage, isLoading } = useQuery({
    queryKey: ["my-usage"],
    queryFn: () => UsersService.readUserMeUsage(),
    retry: false,
  })

  if (isLoading || !usage) return null

  const tokenLimit = usage.limit?.max_tokens_per_month
  const tokenPct = tokenLimit ? usage.tokens_this_month / tokenLimit : 0
  const isBlocked = tokenPct >= 1.0
  const isWarning = tokenPct >= 0.8 && !isBlocked

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">My Usage</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {isBlocked && (
          <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200">
            You have reached your monthly token limit. Rename operations are
            blocked until the next billing period.
          </div>
        )}
        {isWarning && (
          <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            You have used {Math.round(tokenPct * 100)}% of your monthly token
            limit.
          </div>
        )}
        <UsageBar
          current={usage.requests_today}
          limit={usage.limit?.max_requests_per_day ?? null}
          label="requests / day"
        />
        <UsageBar
          current={usage.tokens_this_month}
          limit={usage.limit?.max_tokens_per_month ?? null}
          label="tokens / month"
        />
      </CardContent>
    </Card>
  )
}

function Dashboard() {
  const { user: currentUser } = useAuth()

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl truncate max-w-sm">
          Hi, {currentUser?.full_name || currentUser?.email}
        </h1>
        <p className="text-muted-foreground">Welcome back!</p>
      </div>
      <div className="grid gap-6 md:grid-cols-2">
        <ServiceAccountInfo />
        <MyUsageInfo />
      </div>
    </div>
  )
}
