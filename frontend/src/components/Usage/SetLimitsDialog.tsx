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
  const [validationError, setValidationError] = useState<string | null>(null)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: (payload: {
      max_requests_per_day: number | null
      max_tokens_per_month: number | null
    }) =>
      UsersService.updateUserLimits({
        userId,
        requestBody: payload,
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

  function handleSave() {
    const parsedRequests = requestsPerDay.trim()
      ? Number.parseInt(requestsPerDay, 10)
      : null
    const parsedTokens = tokensPerMonth.trim()
      ? Number.parseInt(tokensPerMonth, 10)
      : null

    if (
      (parsedRequests !== null &&
        (!Number.isInteger(parsedRequests) || parsedRequests < 1)) ||
      (parsedTokens !== null &&
        (!Number.isInteger(parsedTokens) || parsedTokens < 1))
    ) {
      setValidationError("Limits must be positive integers.")
      return
    }

    setValidationError(null)
    mutation.mutate({
      max_requests_per_day: parsedRequests,
      max_tokens_per_month: parsedTokens,
    })
  }

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
              min={1}
              onChange={(e) => {
                setRequestsPerDay(e.target.value)
                setValidationError(null)
              }}
            />
          </div>
          <div className="grid gap-2">
            <Label>Max Tokens / Month</Label>
            <Input
              type="number"
              placeholder="Unlimited"
              value={tokensPerMonth}
              min={1}
              onChange={(e) => {
                setTokensPerMonth(e.target.value)
                setValidationError(null)
              }}
            />
          </div>
          {validationError && (
            <p className="text-destructive text-sm">{validationError}</p>
          )}
        </div>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="outline" disabled={mutation.isPending}>
              Cancel
            </Button>
          </DialogClose>
          <LoadingButton loading={mutation.isPending} onClick={handleSave}>
            Save
          </LoadingButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
