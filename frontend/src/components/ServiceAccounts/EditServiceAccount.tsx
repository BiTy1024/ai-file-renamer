import { zodResolver } from "@hookform/resolvers/zod"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type ServiceAccountPublic, ServiceAccountsService } from "@/client"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { DropdownMenuItem } from "@/components/ui/dropdown-menu"
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form"
import { Input } from "@/components/ui/input"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { CredentialsInput } from "./CredentialsInput"

const formSchema = z.object({
  display_name: z.string().min(1, "Name is required").max(255),
  description: z.string().max(500).optional(),
  credentials_json: z.string().optional(),
})

type FormData = z.infer<typeof formSchema>

interface EditServiceAccountProps {
  serviceAccount: ServiceAccountPublic
  onSuccess: () => void
}

const EditServiceAccount = ({
  serviceAccount,
  onSuccess,
}: EditServiceAccountProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    defaultValues: {
      display_name: serviceAccount.display_name,
      description: serviceAccount.description ?? "",
      credentials_json: "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: FormData) => {
      const submitData: Record<string, unknown> = {
        display_name: data.display_name,
        description: data.description,
      }
      if (data.credentials_json) {
        submitData.credentials_json = data.credentials_json
      }
      return ServiceAccountsService.updateServiceAccount({
        saId: serviceAccount.id,
        requestBody: submitData,
      })
    },
    onSuccess: () => {
      showSuccessToast("Service account updated successfully")
      setIsOpen(false)
      onSuccess()
    },
    onError: handleError.bind(showErrorToast),
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["service-accounts"] })
    },
  })

  const onSubmit = (data: FormData) => {
    mutation.mutate(data)
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DropdownMenuItem
        onSelect={(e) => e.preventDefault()}
        onClick={() => setIsOpen(true)}
      >
        <Pencil />
        Edit
      </DropdownMenuItem>
      <DialogContent className="sm:max-w-lg">
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)}>
            <DialogHeader>
              <DialogTitle>Edit Service Account</DialogTitle>
              <DialogDescription>
                Update the service account details. Leave credentials empty to
                keep existing ones.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <FormField
                control={form.control}
                name="display_name"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      Display Name <span className="text-destructive">*</span>
                    </FormLabel>
                    <FormControl>
                      <Input placeholder="My Service Account" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Description</FormLabel>
                    <FormControl>
                      <Input placeholder="Optional description" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="credentials_json"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Replace Credentials JSON</FormLabel>
                    <FormControl>
                      <CredentialsInput
                        value={field.value ?? ""}
                        onChange={field.onChange}
                        placeholder="Leave empty to keep existing credentials..."
                      />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <DialogFooter>
              <DialogClose asChild>
                <Button variant="outline" disabled={mutation.isPending}>
                  Cancel
                </Button>
              </DialogClose>
              <LoadingButton type="submit" loading={mutation.isPending}>
                Save
              </LoadingButton>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}

export default EditServiceAccount
