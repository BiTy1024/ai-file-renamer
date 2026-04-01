import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { Folder, Info } from "lucide-react"

import { DriveService, ServiceAccountsService } from "@/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
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

function FolderGrid() {
  const {
    data: folderData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ["drive-folders"],
    queryFn: () => DriveService.readFolders(),
    retry: false,
  })

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={`skeleton-${i}`} className="h-24 rounded-lg" />
        ))}
      </div>
    )
  }

  if (error) {
    const message =
      (error as { body?: { detail?: string } })?.body?.detail ??
      "Failed to load folders"
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground">{message}</p>
        </CardContent>
      </Card>
    )
  }

  if (!folderData?.folders?.length) {
    return (
      <Card>
        <CardContent className="py-8 text-center">
          <Folder className="text-muted-foreground mx-auto mb-3 size-10" />
          <p className="text-muted-foreground">
            No folders shared with your service account yet.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {folderData.folders.map((folder) => (
        <Link
          key={folder.id}
          to="/drive/$folderId"
          params={{ folderId: folder.id }}
        >
          <Card className="hover:border-primary/50 cursor-pointer transition-colors">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Folder className="text-primary size-5" />
                {folder.name}
              </CardTitle>
            </CardHeader>
          </Card>
        </Link>
      ))}
    </div>
  )
}

function DrivePage() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Drive</h1>
        <p className="text-muted-foreground">
          Browse folders and files from Google Drive
        </p>
      </div>
      <ServiceAccountPanel />
      <FolderGrid />
    </div>
  )
}
