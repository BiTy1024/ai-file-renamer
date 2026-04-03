import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Loader2 } from "lucide-react"
import { useEffect, useState } from "react"

import { AdminService } from "@/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export function GlobalDefaultLimits() {
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ["admin-settings"],
    queryFn: () => AdminService.readAdminSettings(),
  })

  const [requestsPerDay, setRequestsPerDay] = useState("")
  const [tokensPerMonth, setTokensPerMonth] = useState("")

  useEffect(() => {
    if (data) {
      setRequestsPerDay(data.default_max_requests_per_day?.toString() ?? "")
      setTokensPerMonth(data.default_max_tokens_per_month?.toString() ?? "")
    }
  }, [data])

  const mutation = useMutation({
    mutationFn: () =>
      AdminService.updateSettings({
        requestBody: {
          default_max_requests_per_day: requestsPerDay
            ? Number.parseInt(requestsPerDay, 10)
            : null,
          default_max_tokens_per_month: tokensPerMonth
            ? Number.parseInt(tokensPerMonth, 10)
            : null,
        },
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-settings"] })
    },
  })

  const hasChanges =
    (requestsPerDay || "") !==
      (data?.default_max_requests_per_day?.toString() ?? "") ||
    (tokensPerMonth || "") !==
      (data?.default_max_tokens_per_month?.toString() ?? "")

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          Default Limits for New Users
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="text-muted-foreground text-sm">Loading...</div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="default-requests" className="text-sm">
                  Max requests / day
                </Label>
                <Input
                  id="default-requests"
                  type="number"
                  min="1"
                  placeholder="Unlimited"
                  value={requestsPerDay}
                  onChange={(e) => setRequestsPerDay(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="default-tokens" className="text-sm">
                  Max tokens / month
                </Label>
                <Input
                  id="default-tokens"
                  type="number"
                  min="1"
                  placeholder="Unlimited"
                  value={tokensPerMonth}
                  onChange={(e) => setTokensPerMonth(e.target.value)}
                />
              </div>
            </div>
            <Button
              size="sm"
              onClick={() => mutation.mutate()}
              disabled={!hasChanges || mutation.isPending}
            >
              {mutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              Save Defaults
            </Button>
            <p className="text-muted-foreground text-xs">
              Applied automatically when new users are created. Leave empty for
              unlimited.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
