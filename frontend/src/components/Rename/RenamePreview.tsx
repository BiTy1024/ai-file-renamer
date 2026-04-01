import { AlertTriangle, ArrowRight, Check, X } from "lucide-react"
import { useState } from "react"

import type { RenamePreview as RenamePreviewType } from "@/client"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

interface RenamePreviewProps {
  previews: RenamePreviewType[]
  onConfirm: (renames: { file_id: string; new_name: string }[]) => void
  onCancel: () => void
  isConfirming: boolean
  canConfirm: boolean
}

export function RenamePreview({
  previews,
  onConfirm,
  onCancel,
  isConfirming,
  canConfirm,
}: RenamePreviewProps) {
  const [selected, setSelected] = useState<Set<string>>(() => {
    const initial = new Set<string>()
    for (const p of previews) {
      if (!p.error) initial.add(p.file_id)
    }
    return initial
  })

  const [editedNames, setEditedNames] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {}
    for (const p of previews) {
      initial[p.file_id] = p.proposed_name
    }
    return initial
  })

  const [editingId, setEditingId] = useState<string | null>(null)

  const selectableItems = previews.filter((p) => !p.error)
  const allSelected = selectableItems.every((p) => selected.has(p.file_id))

  const toggleAll = () => {
    if (allSelected) {
      setSelected(new Set())
    } else {
      setSelected(new Set(selectableItems.map((p) => p.file_id)))
    }
  }

  const toggleOne = (fileId: string) => {
    const next = new Set(selected)
    if (next.has(fileId)) {
      next.delete(fileId)
    } else {
      next.add(fileId)
    }
    setSelected(next)
  }

  const handleConfirm = () => {
    const renames = previews
      .filter((p) => selected.has(p.file_id))
      .map((p) => ({
        file_id: p.file_id,
        new_name: editedNames[p.file_id] ?? p.proposed_name,
      }))
    onConfirm(renames)
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">
                <Checkbox
                  checked={allSelected}
                  onCheckedChange={toggleAll}
                  disabled={isConfirming}
                />
              </TableHead>
              <TableHead>Original Name</TableHead>
              <TableHead className="w-8" />
              <TableHead>Proposed Name</TableHead>
              <TableHead className="w-20">Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {previews.map((preview) => (
              <TableRow
                key={preview.file_id}
                className={preview.error ? "opacity-60" : ""}
              >
                <TableCell>
                  <Checkbox
                    checked={selected.has(preview.file_id)}
                    onCheckedChange={() => toggleOne(preview.file_id)}
                    disabled={!!preview.error || isConfirming}
                  />
                </TableCell>
                <TableCell>
                  <span className="text-muted-foreground text-sm">
                    {preview.original_name}
                  </span>
                </TableCell>
                <TableCell>
                  <ArrowRight className="text-muted-foreground size-4" />
                </TableCell>
                <TableCell>
                  {editingId === preview.file_id ? (
                    <div className="flex items-center gap-2">
                      <Input
                        value={editedNames[preview.file_id] ?? ""}
                        onChange={(e) =>
                          setEditedNames((prev) => ({
                            ...prev,
                            [preview.file_id]: e.target.value,
                          }))
                        }
                        className="h-8 text-sm"
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === "Enter" || e.key === "Escape") {
                            setEditingId(null)
                          }
                        }}
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8"
                        onClick={() => setEditingId(null)}
                      >
                        <Check className="size-4" />
                      </Button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="hover:bg-muted cursor-pointer rounded px-1 py-0.5 text-left text-sm font-medium"
                      onClick={() =>
                        !isConfirming && setEditingId(preview.file_id)
                      }
                      title="Click to edit"
                    >
                      {editedNames[preview.file_id] ?? preview.proposed_name}
                    </button>
                  )}
                </TableCell>
                <TableCell>
                  {preview.error ? (
                    <TooltipProvider>
                      <Tooltip>
                        <TooltipTrigger>
                          <AlertTriangle className="size-4 text-amber-500" />
                        </TooltipTrigger>
                        <TooltipContent>{preview.error}</TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  ) : (
                    <Check className="size-4 text-green-500" />
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="flex items-center justify-between">
        <p className="text-muted-foreground text-sm">
          {selected.size} of {selectableItems.length} files selected
        </p>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onCancel} disabled={isConfirming}>
            <X className="mr-2 size-4" />
            Cancel
          </Button>
          {canConfirm ? (
            <LoadingButton
              onClick={handleConfirm}
              loading={isConfirming}
              disabled={selected.size === 0}
            >
              Confirm Rename ({selected.size})
            </LoadingButton>
          ) : (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span>
                    <Button disabled>Confirm Rename</Button>
                  </span>
                </TooltipTrigger>
                <TooltipContent>Viewers cannot execute renames</TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
        </div>
      </div>
    </div>
  )
}
