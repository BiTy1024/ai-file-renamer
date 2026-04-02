import { useQuery } from "@tanstack/react-query"
import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { Info } from "lucide-react"
import { useState } from "react"
import { ServiceAccountsService } from "@/client"
import { FolderSearch } from "@/components/Drive/FolderSearch"
import { FolderTree } from "@/components/Drive/FolderTree"
import { Card, CardContent } from "@/components/ui/card"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/drive")({
  component: DrivePage,
  head: () => ({
    meta: [{ title: "Drive - AI-Namer" }],
  }),
})

function ServiceAccountPanel() {
  const { user } = useAuth()
  const { data: sa } = useQuery({
    queryKey: ["my-service-account"],
    queryFn: () => ServiceAccountsService.readOwnServiceAccount(),
    retry: false,
  })

  if (!sa || user?.role === "viewer") return null

  return (
    <Card className="border-accent/30 bg-accent/5">
      <CardContent className="flex items-center gap-3 py-3">
        <Info className="text-accent size-5 shrink-0" />
        <p className="text-sm">
          Share folders with{" "}
          <code className="bg-muted rounded px-1.5 py-0.5 text-xs font-medium">
            {sa.client_email}
          </code>{" "}
          to make them visible here.
        </p>
      </CardContent>
    </Card>
  )
}

function DrivePage() {
  const navigate = useNavigate()
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null)

  function handleFolderSelect(folderId: string) {
    setSelectedFolderId(folderId)
    navigate({ to: "/drive-folder/$folderId", params: { folderId } })
  }

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Drive</h1>
        <p className="text-muted-foreground">
          Browse folders and files from Google Drive
        </p>
      </div>
      <ServiceAccountPanel />
      <FolderSearch onSelect={handleFolderSelect} />
      <FolderTree
        selectedFolderId={selectedFolderId}
        onSelect={handleFolderSelect}
      />
    </div>
  )
}
