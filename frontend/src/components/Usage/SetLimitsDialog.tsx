import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Settings } from "lucide-react"
import { useState } from "react"

import { UsersService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

interface SetLimitsDialogProps {
  userId: string
  userEmail: string
  currentRequestsPerDay: number | null
  currentTokensPerMonth: number | null
}

export function SetLimitsDialog({
  userId,
  userEmail,
  currentRequestsPerDay,
  currentTokensPerMonth,
}: SetLimitsDialogProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [requestsPerDay, setRequestsPerDay] = useState(
    currentRequestsPerDay?.toString() ?? "",
  )
  const [tokensPerMonth, setTokensPerMonth] = useState(
    currentTokensPerMonth?.toString() ?? "",
  )
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () =>
      UsersService.updateUserLimits({
        userId,
        requestBody: {
          max_requests_per_day: requestsPerDay
            ? Number.parseInt(requestsPerDay, 10)
            : null,
          max_tokens_per_month: tokensPerMonth
            ? Number.parseInt(tokensPerMonth, 10)
            : null,
        },
      }),
    onSuccess: () => {
      showSuccessToast("Limits updated successfully")
      setIsOpen(false)
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["user-usage"] })
    },
  })

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="size-8">
          <Settings className="size-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Set Rate Limits</DialogTitle>
          <DialogDescription>
            Configure limits for {userEmail}. Leave empty for unlimited.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label>Max Requests / Day</Label>
            <Input
              type="number"
              placeholder="Unlimited"
              value={requestsPerDay}
              onChange={(e) => setRequestsPerDay(e.target.value)}
            />
          </div>
          <div className="grid gap-2">
            <Label>Max Tokens / Month</Label>
            <Input
              type="number"
              placeholder="Unlimited"
              value={tokensPerMonth}
              onChange={(e) => setTokensPerMonth(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" disabled={mutation.isPending}>
              Cancel
            </Button>
          </DialogClose>
          <LoadingButton
            loading={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            Save
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
