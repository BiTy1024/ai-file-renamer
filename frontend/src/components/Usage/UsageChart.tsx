import { useQuery } from "@tanstack/react-query"
import { useState } from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { AdminService } from "@/client"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"

type ChartMode = "tokens" | "cost"

export function UsageChart({ userId }: { userId?: string }) {
  const [period, setPeriod] = useState("daily")
  const [range, setRange] = useState("30d")
  const [mode, setMode] = useState<ChartMode>("tokens")

  const { data, isLoading } = useQuery({
    queryKey: ["admin-usage-timeseries", period, range, userId],
    queryFn: () =>
      userId
        ? AdminService.readUserUsageTimeseries({
            userId,
            period,
            range,
          })
        : AdminService.readUsageTimeseries({ period, range }),
  })

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <CardTitle className="text-base">
            {userId ? "User Usage Over Time" : "Usage Over Time"}
          </CardTitle>
          <div className="flex items-center gap-2">
            <Tabs value={mode} onValueChange={(v) => setMode(v as ChartMode)}>
              <TabsList className="h-8">
                <TabsTrigger value="tokens" className="text-xs">
                  Tokens
                </TabsTrigger>
                <TabsTrigger value="cost" className="text-xs">
                  Cost
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <Select value={period} onValueChange={setPeriod}>
              <SelectTrigger className="h-8 w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
              </SelectContent>
            </Select>
            <Select value={range} onValueChange={setRange}>
              <SelectTrigger className="h-8 w-20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="30d">30d</SelectItem>
                <SelectItem value="90d">90d</SelectItem>
                <SelectItem value="1y">1y</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-[300px] w-full" />
        ) : !data || data.length === 0 ? (
          <div className="text-muted-foreground flex h-[300px] items-center justify-center text-sm">
            No usage data for this period
          </div>
        ) : mode === "tokens" ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="date"
                className="text-xs"
                tickFormatter={(v) => {
                  const d = new Date(v)
                  return `${d.getMonth() + 1}/${d.getDate()}`
                }}
              />
              <YAxis
                className="text-xs"
                tickFormatter={(v) =>
                  v >= 1000 ? `${(v / 1000).toFixed(0)}K` : v
                }
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                  color: "hsl(var(--popover-foreground))",
                }}
                formatter={(value, name) => [
                  Number(value).toLocaleString(),
                  name === "input_tokens" ? "Input" : "Output",
                ]}
              />
              <Bar
                dataKey="input_tokens"
                fill="hsl(var(--chart-1))"
                stackId="tokens"
                radius={[0, 0, 0, 0]}
              />
              <Bar
                dataKey="output_tokens"
                fill="hsl(var(--chart-2))"
                stackId="tokens"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis
                dataKey="date"
                className="text-xs"
                tickFormatter={(v) => {
                  const d = new Date(v)
                  return `${d.getMonth() + 1}/${d.getDate()}`
                }}
              />
              <YAxis
                className="text-xs"
                tickFormatter={(v) => `$${v.toFixed(2)}`}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(var(--popover))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: "var(--radius)",
                  color: "hsl(var(--popover-foreground))",
                }}
                formatter={(value) => [`$${Number(value).toFixed(4)}`, "Cost"]}
              />
              <Line
                type="monotone"
                dataKey="cost"
                stroke="hsl(var(--chart-3))"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  )
}
