import { useQuery } from "@tanstack/react-query"
import { Folder } from "lucide-react"

import { DriveService } from "@/client"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

import { FolderTreeNode } from "./FolderTreeNode"

interface FolderTreeProps {
  selectedFolderId: string | null
  onSelect: (folderId: string) => void
}

export function FolderTree({ selectedFolderId, onSelect }: FolderTreeProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["drive-folders"],
    queryFn: () => DriveService.readFolders(),
    retry: false,
  })

  if (isLoading) {
    return (
      <div className="flex flex-col gap-1">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={`skel-${i}`} className="h-8 w-full rounded-md" />
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

  if (!data?.folders?.length) {
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
    <div className="rounded-md border">
      {data.folders.map((folder) => (
        <FolderTreeNode
          key={folder.id}
          folderId={folder.id}
          folderName={folder.name}
          depth={0}
          selectedFolderId={selectedFolderId}
          onSelect={onSelect}
        />
      ))}
    </div>
  )
}
