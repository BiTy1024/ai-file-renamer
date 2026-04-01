import { AlertTriangle, Coffee } from "lucide-react"

import { Card, CardContent } from "@/components/ui/card"

interface RenameProgressProps {
  fileCount: number
}

function estimateTime(fileCount: number): string {
  const avgSecondsPerFile = 15
  const totalSeconds = fileCount * avgSecondsPerFile
  if (totalSeconds < 60) return `~${totalSeconds} seconds`
  const minutes = Math.ceil(totalSeconds / 60)
  return `~${minutes} minute${minutes > 1 ? "s" : ""}`
}

export function RenameProgress({ fileCount }: RenameProgressProps) {
  return (
    <Card>
      <CardContent className="flex flex-col items-center gap-4 py-10">
        <Coffee className="text-primary size-10 animate-bounce" />
        <div className="text-center">
          <p className="text-lg font-medium">
            Grab a coffee while AI analyzes {fileCount} file
            {fileCount !== 1 ? "s" : ""}...
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
