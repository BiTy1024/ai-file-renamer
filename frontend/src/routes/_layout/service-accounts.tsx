import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Suspense } from "react"

import { ServiceAccountsService, UsersService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import PendingUsers from "@/components/Pending/PendingUsers"
import AddServiceAccount from "@/components/ServiceAccounts/AddServiceAccount"
import { columns } from "@/components/ServiceAccounts/columns"

function getServiceAccountsQueryOptions() {
  return {
    queryFn: () =>
      ServiceAccountsService.readServiceAccounts({ skip: 0, limit: 100 }),
    queryKey: ["service-accounts"],
  }
}

export const Route = createFileRoute("/_layout/service-accounts")({
  component: ServiceAccountsPage,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (user.role !== "admin") {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Service Accounts - AI-Namer" }],
  }),
})

function ServiceAccountsTableContent() {
  const { data: serviceAccounts } = useSuspenseQuery(
    getServiceAccountsQueryOptions(),
  )

  return <DataTable columns={columns} data={serviceAccounts.data} />
}

function ServiceAccountsTable() {
  return (
    <Suspense fallback={<PendingUsers />}>
      <ServiceAccountsTableContent />
    </Suspense>
  )
}

function ServiceAccountsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Service Accounts
          </h1>
          <p className="text-muted-foreground">
            Manage Google service accounts and assign them to users
          </p>
        </div>
        <AddServiceAccount />
      </div>
      <ServiceAccountsTable />
    </div>
  )
}
