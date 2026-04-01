import { AlertTriangle, Loader2 } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"

interface RenameProgressProps {
  fileCount: number
}

function estimateTime(fileCount: number): string {
  // Rough estimates: ~5s per image (download + Claude Vision), ~3s per PDF
  const avgSecondsPerFile = 5
  const totalSeconds = fileCount * avgSecondsPerFile
  if (totalSeconds < 60) return `~${totalSeconds} seconds`
  const minutes = Math.ceil(totalSeconds / 60)
  return `~${minutes} minute${minutes > 1 ? "s" : ""}`
}

export function RenameProgress({ fileCount }: RenameProgressProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-4 py-8">
        <Loader2 className="text-primary size-8 animate-spin" />
        <div className="text-center">
          <p className="font-medium">
            Analyzing {fileCount} file{fileCount !== 1 ? "s" : ""} with AI...
          </p>
          <p className="text-muted-foreground text-sm">
            Estimated time: {estimateTime(fileCount)}
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-4 py-2">
          <AlertTriangle className="size-4 text-amber-500" />
          <p className="text-sm text-amber-500">
            Please do not close this window while processing
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
