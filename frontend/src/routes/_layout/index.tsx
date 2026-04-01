import { useQuery } from "@tanstack/react-query"
import { createFileRoute } from "@tanstack/react-router"

import { ServiceAccountsService } from "@/client"
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
      <ServiceAccountInfo />
    </div>
  )
}
