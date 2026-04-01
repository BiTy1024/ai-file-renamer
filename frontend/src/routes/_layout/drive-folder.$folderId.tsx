import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  File,
  FileText,
  Image,
  Presentation,
  Sheet,
} from "lucide-react"

import { DriveService } from "@/client"
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

export const Route = createFileRoute("/_layout/drive-folder/$folderId")({
  component: FolderFilesPage,
  head: () => ({
    meta: [{ title: "Files - AI-Namer" }],
  }),
})

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

function FolderFilesPage() {
  const { folderId } = Route.useParams()

  const { data, isLoading, error } = useQuery({
    queryKey: ["drive-files", folderId],
    queryFn: () => DriveService.readFolderFiles({ folderId }),
    retry: false,
  })

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

      {isLoading && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={`skeleton-${i}`} className="h-12 rounded" />
          ))}
        </div>
      )}

      {error && (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-muted-foreground">
              {(error as { body?: { detail?: string } })?.body?.detail ??
                "Failed to load files"}
            </p>
          </CardContent>
        </Card>
      )}

      {data && !data.files?.length && (
        <Card>
          <CardContent className="py-8 text-center">
            <File className="text-muted-foreground mx-auto mb-3 size-10" />
            <p className="text-muted-foreground">No files in this folder.</p>
          </CardContent>
        </Card>
      )}

      {data && data.files?.length > 0 && (
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
              {data.files.map((file) => {
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
      )}
    </div>
  )
}
