import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

interface UsageBarProps {
  current: number
  limit: number | null
  label: string
}

export function UsageBar({ current, limit, label }: UsageBarProps) {
  if (!limit) {
    return (
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground text-sm">{current}</span>
        <Badge variant="secondary" className="text-xs">
          Unlimited
        </Badge>
      </div>
    )
  }

  const percentage = Math.min((current / limit) * 100, 100)
  const color =
    percentage >= 80
      ? "bg-red-500"
      : percentage >= 50
        ? "bg-amber-500"
        : "bg-green-500"

  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-sm">
        <span>
          {current} / {limit}
        </span>
        <span className="text-muted-foreground text-xs">{label}</span>
      </div>
      <div className="bg-muted h-2 w-full rounded-full">
        <div
          className={cn("h-2 rounded-full transition-all", color)}
          style={{ width: `${percentage}%` }}
        />
      </div>
    </div>
  )
}
