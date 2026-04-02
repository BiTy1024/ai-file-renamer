import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  File,
  FileText,
  Image,
  Presentation,
  Sheet,
} from "lucide-react"
import { useState } from "react"

import {
  DriveService,
  type RenamePreview as RenamePreviewType,
  RenameService,
} from "@/client"
import { RenameForm } from "@/components/Rename/RenameForm"
import { RenamePreview } from "@/components/Rename/RenamePreview"
import { RenameProgress } from "@/components/Rename/RenameProgress"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import useAuth from "@/hooks/useAuth"
import useCustomToast from "@/hooks/useCustomToast"

export const Route = createFileRoute("/_layout/drive-folder/$folderId")({
  component: FolderFilesPage,
  head: () => ({
    meta: [{ title: "Files - AI-Namer" }],
  }),
})

type RenameState = "idle" | "loading" | "preview" | "confirming"

function getFileIcon(mimeType: string) {
  if (mimeType.startsWith("image/")) return Image
  if (mimeType.includes("spreadsheet") || mimeType.includes("csv")) return Sheet
  if (mimeType.includes("presentation") || mimeType.includes("slides"))
    return Presentation
  if (
    mimeType.includes("document") ||
    mimeType.includes("pdf") ||
    mimeType.includes("text")
  )
    return FileText
  return File
}

function formatFileSize(sizeStr: string | null | undefined): string {
  if (!sizeStr) return "-"
  const bytes = Number.parseInt(sizeStr, 10)
  if (Number.isNaN(bytes)) return "-"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024)
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "-"
  return new Date(dateStr).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  })
}

function FileTable({
  files,
}: {
  files: {
    id: string
    name: string
    mime_type: string
    size?: string | null
    modified_time?: string | null
  }[]
}) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Name</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Modified</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {files.map((file) => {
            const Icon = getFileIcon(file.mime_type)
            return (
              <TableRow key={file.id}>
                <TableCell>
                  <div className="flex items-center gap-2">
                    <Icon className="text-muted-foreground size-4 shrink-0" />
                    <span className="font-medium">{file.name}</span>
                  </div>
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {file.mime_type
                    .split("/")
                    .pop()
                    ?.replace("vnd.google-apps.", "")}
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {formatFileSize(file.size)}
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {formatDate(file.modified_time)}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}

function FolderFilesPage() {
  const { folderId } = Route.useParams()
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const [renameState, setRenameState] = useState<RenameState>("idle")
  const [previews, setPreviews] = useState<RenamePreviewType[]>([])

  const { data, isLoading, error } = useQuery({
    queryKey: ["drive-files", folderId],
    queryFn: () => DriveService.readFolderFiles({ folderId }),
    retry: false,
  })

  const previewMutation = useMutation({
    mutationFn: (params: {
      convention: string
      instruction: string
      contentType: string
    }) =>
      RenameService.renamePreview({
        requestBody: {
          folder_id: folderId,
          convention: params.convention,
          instruction: params.instruction || undefined,
          content_type: params.contentType || undefined,
        },
      }),
    onSuccess: (response) => {
      setPreviews(response.previews)
      setRenameState("preview")
    },
    onError: (err) => {
      const message =
        (err as { body?: { detail?: string } })?.body?.detail ??
        "Failed to generate preview"
      showErrorToast(message)
      setRenameState("idle")
    },
  })

  const confirmMutation = useMutation({
    mutationFn: (
      renames: { file_id: string; new_name: string; original_name: string }[],
    ) =>
      RenameService.renameConfirm({
        requestBody: { folder_id: folderId, renames },
      }),
    onSuccess: (response) => {
      const succeeded = response.results.filter((r) => r.success).length
      const failed = response.results.filter((r) => !r.success).length
      if (succeeded > 0) {
        showSuccessToast(`${succeeded} file(s) renamed successfully`)
      }
      if (failed > 0) {
        showErrorToast(`${failed} file(s) failed to rename`)
      }
      queryClient.invalidateQueries({ queryKey: ["drive-files", folderId] })
      setPreviews([])
      setRenameState("idle")
    },
    onError: (err) => {
      const message =
        (err as { body?: { detail?: string } })?.body?.detail ??
        "Failed to confirm renames"
      showErrorToast(message)
      setRenameState("preview")
    },
  })

  const handlePreview = (
    convention: string,
    instruction: string,
    contentType: string,
  ) => {
    setRenameState("loading")
    previewMutation.mutate({ convention, instruction, contentType })
  }

  const handleConfirm = (
    renames: { file_id: string; new_name: string; original_name: string }[],
  ) => {
    setRenameState("confirming")
    confirmMutation.mutate(renames)
  }

  const handleCancel = () => {
    setPreviews([])
    setRenameState("idle")
  }

  const canConfirm = user?.role !== "viewer"

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-4">
        <Link to="/drive">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="size-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Files</h1>
          <p className="text-muted-foreground">Files in the selected folder</p>
        </div>
      </div>

      {/* Rename form — always visible in idle/loading */}
      {(renameState === "idle" || renameState === "loading") &&
        data &&
        data.files?.length > 0 && (
          <RenameForm
            onPreview={handlePreview}
            disabled={renameState === "loading"}
          />
        )}

      {/* Initial file loading */}
      {isLoading && renameState === "idle" && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={`skeleton-${i}`} className="h-12 rounded" />
          ))}
        </div>
      )}

      {/* AI processing progress */}
      {renameState === "loading" && (
        <RenameProgress fileCount={data?.files?.length ?? 0} />
      )}

      {/* Error state */}
      {error && renameState === "idle" && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">
              {(error as { body?: { detail?: string } })?.body?.detail ??
                "Failed to load files"}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Empty state */}
      {data && !data.files?.length && renameState === "idle" && (
        <Card>
          <CardContent className="py-8 text-center">
            <File className="text-muted-foreground mx-auto mb-3 size-10" />
            <p className="text-muted-foreground">No files in this folder.</p>
          </CardContent>
        </Card>
      )}

      {/* Preview table */}
      {(renameState === "preview" || renameState === "confirming") && (
        <RenamePreview
          previews={previews}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
          isConfirming={renameState === "confirming"}
          canConfirm={canConfirm}
        />
      )}

      {/* Normal file table — only in idle state */}
      {renameState === "idle" &&
        !isLoading &&
        data &&
        data.files?.length > 0 && <FileTable files={data.files} />}
    </div>
  )
}
