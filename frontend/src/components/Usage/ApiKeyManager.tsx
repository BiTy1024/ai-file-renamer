import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { Check, Key, Loader2, Trash2, X } from "lucide-react"
import { useState } from "react"

import { AdminService } from "@/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"

export function ApiKeyManager() {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [apiKey, setApiKey] = useState("")
  const [validationResult, setValidationResult] = useState<{
    valid: boolean
    error?: string | null
  } | null>(null)

  const { data: status, isLoading } = useQuery({
    queryKey: ["admin-api-key-status"],
    queryFn: () => AdminService.readApiKeyStatus(),
  })

  const updateMutation = useMutation({
    mutationFn: (key: string) =>
      AdminService.updateApiKey({ requestBody: { api_key: key } }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-api-key-status"] })
      setOpen(false)
      setApiKey("")
      setValidationResult(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: () => AdminService.removeApiKey(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-api-key-status"] })
    },
  })

  const validateMutation = useMutation({
    mutationFn: (key: string) =>
      AdminService.validateApiKey({ requestBody: { api_key: key } }),
    onSuccess: (result) => {
      setValidationResult(result)
    },
  })

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-base">Claude API Key</CardTitle>
        <div className="flex items-center gap-2">
          {status?.is_set && status.source === "database" && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <Key className="mr-2 h-4 w-4" />
                {status?.is_set ? "Update Key" : "Set Key"}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Set Claude API Key</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <Input
                  type="password"
                  placeholder="sk-ant-api03-..."
                  value={apiKey}
                  onChange={(e) => {
                    setApiKey(e.target.value)
                    setValidationResult(null)
                  }}
                />
                {validationResult && (
                  <div
                    className={`flex items-center gap-2 text-sm ${validationResult.valid ? "text-green-600" : "text-red-600"}`}
                  >
                    {validationResult.valid ? (
                      <Check className="h-4 w-4" />
                    ) : (
                      <X className="h-4 w-4" />
                    )}
                    {validationResult.valid
                      ? "Key is valid"
                      : (validationResult.error ?? "Invalid key")}
                  </div>
                )}
              </div>
              <DialogFooter className="gap-2">
                <Button
                  variant="outline"
                  onClick={() => validateMutation.mutate(apiKey)}
                  disabled={!apiKey || validateMutation.isPending}
                >
                  {validateMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Validate
                </Button>
                <Button
                  onClick={() => updateMutation.mutate(apiKey)}
                  disabled={!apiKey || updateMutation.isPending}
                >
                  {updateMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Save
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="text-muted-foreground text-sm">Loading...</div>
        ) : status?.is_set ? (
          <div className="flex items-center gap-3">
            <code className="bg-muted rounded px-2 py-1 text-sm">
              {status.masked_key}
            </code>
            <Badge variant={status.source === "env" ? "secondary" : "default"}>
              {status.source === "env" ? "Environment Variable" : "Database"}
            </Badge>
          </div>
        ) : (
          <p className="text-muted-foreground text-sm">
            No API key configured. Set one to enable Claude AI features.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
