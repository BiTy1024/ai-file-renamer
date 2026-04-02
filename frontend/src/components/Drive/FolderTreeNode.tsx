import { useQuery } from "@tanstack/react-query"
import { ChevronDown, ChevronRight, Folder } from "lucide-react"
import { useState } from "react"

import { DriveService } from "@/client"
import { cn } from "@/lib/utils"

interface FolderTreeNodeProps {
  folderId: string
  folderName: string
  depth: number
  selectedFolderId: string | null
  onSelect: (folderId: string) => void
}

export function FolderTreeNode({
  folderId,
  folderName,
  depth,
  selectedFolderId,
  onSelect,
}: FolderTreeNodeProps) {
  const [isExpanded, setIsExpanded] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ["subfolders", folderId],
    queryFn: () => DriveService.readFolderSubfolders({ folderId }),
    enabled: isExpanded,
  })

  const isLeaf = data && data.folders.length === 0
  const isSelected = selectedFolderId === folderId

  return (
    <div>
      <div
        className={cn(
          "flex cursor-pointer items-center gap-1 rounded-md px-2 py-1.5 text-sm transition-colors hover:bg-accent",
          isSelected && "bg-accent font-medium",
        )}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
      >
        <button
          type="button"
          className="flex size-4 shrink-0 items-center justify-center text-muted-foreground"
          onClick={(e) => {
            e.stopPropagation()
            if (!isLeaf) setIsExpanded((prev) => !prev)
          }}
          aria-label={isExpanded ? "Collapse" : "Expand"}
        >
          {isLoading ? (
            <span className="size-3 animate-spin rounded-full border border-muted-foreground border-t-transparent" />
          ) : isLeaf ? null : isExpanded ? (
            <ChevronDown className="size-4" />
          ) : (
            <ChevronRight className="size-4" />
          )}
        </button>

        <button
          type="button"
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
          onClick={() => onSelect(folderId)}
        >
          <Folder
            className={cn(
              "size-4 shrink-0",
              isSelected ? "text-primary" : "text-muted-foreground",
            )}
          />
          <span className="truncate">{folderName}</span>
        </button>
      </div>

      {isExpanded && data && data.folders.length > 0 && (
        <div>
          {data.folders.map((child) => (
            <FolderTreeNode
              key={child.id}
              folderId={child.id}
              folderName={child.name}
              depth={depth + 1}
              selectedFolderId={selectedFolderId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  )
}
