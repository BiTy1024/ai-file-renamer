import { useQuery } from "@tanstack/react-query"
import { Folder, Search } from "lucide-react"
import { useEffect, useState } from "react"

import { DriveService } from "@/client"
import { Input } from "@/components/ui/input"

interface FolderSearchProps {
  onSelect: (folderId: string) => void
}

function useDebounce(value: string, delay: number): string {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

export function FolderSearch({ onSelect }: FolderSearchProps) {
  const [inputValue, setInputValue] = useState("")
  const debouncedQuery = useDebounce(inputValue, 300)
  const isActive = debouncedQuery.length >= 2

  const { data, isLoading } = useQuery({
    queryKey: ["folder-search", debouncedQuery],
    queryFn: () => DriveService.searchDriveFolders({ q: debouncedQuery }),
    enabled: isActive,
  })

  function handleSelect(folderId: string) {
    setInputValue("")
    onSelect(folderId)
  }

  return (
    <div className="flex flex-col gap-2">
      <div className="relative">
        <Search className="text-muted-foreground absolute left-2.5 top-2.5 size-4" />
        <Input
          placeholder="Search folders..."
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          className="pl-8"
        />
      </div>

      {isActive && (
        <div className="rounded-md border">
          {isLoading && (
            <div className="text-muted-foreground px-3 py-4 text-center text-sm">
              Searching...
            </div>
          )}

          {!isLoading && data?.results.length === 0 && (
            <div className="text-muted-foreground px-3 py-4 text-center text-sm">
              No folders found for "{debouncedQuery}"
            </div>
          )}

          {!isLoading &&
            data?.results.map((result) => (
              <button
                key={result.id}
                type="button"
                className="hover:bg-accent flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition-colors"
                onClick={() => handleSelect(result.id)}
              >
                <Folder className="text-muted-foreground size-4 shrink-0" />
                <span className="truncate">
                  {result.parent_name ? (
                    <>
                      <span className="text-muted-foreground">
                        {result.parent_name} /{" "}
                      </span>
                      {result.name}
                    </>
                  ) : (
                    result.name
                  )}
                </span>
              </button>
            ))}
        </div>
      )}
    </div>
  )
}
