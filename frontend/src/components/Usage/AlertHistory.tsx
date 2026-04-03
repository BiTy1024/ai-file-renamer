import { useQuery } from "@tanstack/react-query"

import { AdminService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const ALERT_LABELS: Record<string, string> = {
  user_80_pct: "80% Limit",
  user_100_pct: "100% Limit",
  global_spend: "Spend Threshold",
}

const ALERT_VARIANTS: Record<
  string,
  "default" | "secondary" | "destructive" | "outline"
> = {
  user_80_pct: "secondary",
  user_100_pct: "destructive",
  global_spend: "default",
}

export function AlertHistory() {
  const { data, isLoading } = useQuery({
    queryKey: ["admin-alerts"],
    queryFn: () => AdminService.readAlertHistory({ limit: 10 }),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Recent Alerts</CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-24 w-full" />
        ) : !data?.data || data.data.length === 0 ? (
          <p className="text-muted-foreground text-sm">No alerts triggered</p>
        ) : (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Period</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.data.map((alert) => (
                  <TableRow key={alert.id}>
                    <TableCell className="text-muted-foreground text-xs whitespace-nowrap">
                      {alert.created_at
                        ? new Date(alert.created_at).toLocaleString()
                        : "-"}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={ALERT_VARIANTS[alert.alert_type] ?? "outline"}
                      >
                        {ALERT_LABELS[alert.alert_type] ?? alert.alert_type}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">
                      {alert.user_email ?? "-"}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-xs">
                      {alert.period}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
