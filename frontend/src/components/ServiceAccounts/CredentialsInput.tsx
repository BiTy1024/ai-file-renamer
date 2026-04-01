import { Upload } from "lucide-react"
import { useRef, useState } from "react"

import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface CredentialsInputProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function CredentialsInput({
  value,
  onChange,
  placeholder = "Paste the Google service account JSON here...",
}: CredentialsInputProps) {
  const [tab, setTab] = useState<string>("paste")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (event) => {
      const content = event.target?.result
      if (typeof content === "string") {
        onChange(content)
        setTab("paste")
      }
    }
    reader.readAsText(file)
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  return (
    <Tabs value={tab} onValueChange={setTab}>
      <TabsList className="mb-2 w-full">
        <TabsTrigger value="paste" className="flex-1">
          Paste JSON
        </TabsTrigger>
        <TabsTrigger value="upload" className="flex-1">
          Upload File
        </TabsTrigger>
      </TabsList>
      <TabsContent value="paste">
        <textarea
          className="border-input bg-background flex min-h-[120px] w-full rounded-md border px-3 py-2 text-sm"
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </TabsContent>
      <TabsContent value="upload">
        <div className="flex flex-col items-center gap-3 rounded-md border border-dashed p-6">
          <Upload className="text-muted-foreground size-8" />
          <p className="text-muted-foreground text-sm">
            Select a .json service account file
          </p>
          <Button
            type="button"
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
          >
            Choose File
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            className="hidden"
            onChange={handleFileChange}
            data-testid="credentials-file-input"
          />
          {value && (
            <p className="text-sm text-green-600">File loaded successfully</p>
          )}
        </div>
      </TabsContent>
    </Tabs>
  )
}
