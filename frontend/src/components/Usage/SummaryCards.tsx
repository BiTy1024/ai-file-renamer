import { useQuery } from "@tanstack/react-query"

import { AdminService } from "@/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toString()
}

function formatCost(n: number): string {
  return `$${n.toFixed(2)}`
}

function StatCard({
  title,
  value,
  subtitle,
  isLoading,
}: {
  title: string
  value: string
  subtitle?: string
  isLoading: boolean
}) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-muted-foreground text-sm font-medium">
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-8 w-24" />
        ) : (
          <>
            <div className="text-2xl font-bold">{value}</div>
            {subtitle && (
              <p className="text-muted-foreground text-xs">{subtitle}</p>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}

export function SummaryCards() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-usage-summary"],
    queryFn: () => AdminService.readUsageSummary(),
  })

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="Tokens This Month"
        value={formatTokens(data?.current_month_tokens ?? 0)}
        subtitle={`Previous: ${formatTokens(data?.previous_month_tokens ?? 0)}`}
        isLoading={isLoading}
      />
      <StatCard
        title="Cost This Month"
        value={formatCost(data?.current_month_cost ?? 0)}
        subtitle={`Previous: ${formatCost(data?.previous_month_cost ?? 0)}`}
        isLoading={isLoading}
      />
      <StatCard
        title="All-Time Tokens"
        value={formatTokens(data?.all_time_tokens ?? 0)}
        isLoading={isLoading}
      />
      <StatCard
        title="All-Time Cost"
        value={formatCost(data?.all_time_cost ?? 0)}
        isLoading={isLoading}
      />
    </div>
  )
}
