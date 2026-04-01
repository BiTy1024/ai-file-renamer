import { useSuspenseQuery } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"
import { Suspense } from "react"

import { PresetsService, UsersService } from "@/client"
import { DataTable } from "@/components/Common/DataTable"
import PendingUsers from "@/components/Pending/PendingUsers"
import AddPreset from "@/components/Presets/AddPreset"
import { columns } from "@/components/Presets/columns"

function getPresetsQueryOptions() {
  return {
    queryFn: () => PresetsService.readPresets({ skip: 0, limit: 100 }),
    queryKey: ["presets"],
  }
}

export const Route = createFileRoute("/_layout/presets")({
  component: PresetsPage,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (user.role !== "admin") {
      throw redirect({ to: "/" })
    }
  },
  head: () => ({
    meta: [{ title: "Presets - AI-Namer" }],
  }),
})

function PresetsTableContent() {
  const { data: presets } = useSuspenseQuery(getPresetsQueryOptions())
  return <DataTable columns={columns} data={presets.data} />
}

function PresetsTable() {
  return (
    <Suspense fallback={<PendingUsers />}>
      <PresetsTableContent />
    </Suspense>
  )
}

function PresetsPage() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Convention Presets
          </h1>
          <p className="text-muted-foreground">
            Manage reusable naming conventions for file renaming
          </p>
        </div>
        <AddPreset />
      </div>
      <PresetsTable />
    </div>
  )
}
