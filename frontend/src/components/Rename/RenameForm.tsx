import { useQuery } from "@tanstack/react-query"
import { Sparkles } from "lucide-react"
import { useState } from "react"

import { PresetsService } from "@/client"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface RenameFormProps {
  onPreview: (
    convention: string,
    instruction: string,
    contentType: string,
  ) => void
  disabled: boolean
}

export function RenameForm({ onPreview, disabled }: RenameFormProps) {
  const [selectedPresetId, setSelectedPresetId] = useState<string>("custom")
  const [convention, setConvention] = useState("")
  const [instruction, setInstruction] = useState("")
  const [contentType, setContentType] = useState("")

  const { data: presetsData } = useQuery({
    queryKey: ["presets"],
    queryFn: () => PresetsService.readPresets({ skip: 0, limit: 100 }),
  })

  const presets = presetsData?.data ?? []

  const handlePresetChange = (presetId: string) => {
    setSelectedPresetId(presetId)
    if (presetId === "custom") {
      setConvention("")
      setContentType("")
      return
    }
    const preset = presets.find((p) => p.id === presetId)
    if (preset) {
      setConvention(preset.convention)
      setContentType(preset.content_type ?? "")
    }
  }

  const handleSubmit = () => {
    if (!convention.trim()) return
    onPreview(convention, instruction, contentType)
  }

  return (
    <Card>
      <CardContent className="grid gap-4 py-4">
        <div className="grid gap-2">
          <Label>Preset</Label>
          <Select
            value={selectedPresetId}
            onValueChange={handlePresetChange}
            disabled={disabled}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a preset or use custom" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="custom">Custom Convention</SelectItem>
              {presets.map((preset) => (
                <SelectItem key={preset.id} value={preset.id}>
                  {preset.name}
                  {preset.content_type ? ` (${preset.content_type})` : ""}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid gap-2">
          <Label>
            Convention <span className="text-destructive">*</span>
          </Label>
          <Input
            value={convention}
            onChange={(e) => setConvention(e.target.value)}
            placeholder="[INVOICE_DATE]_[TOTAL]_[COMPANY]"
            disabled={disabled}
          />
          <p className="text-muted-foreground text-xs">
            Use [FIELD_NAME] placeholders. The AI will extract these fields from
            each file.
          </p>
        </div>

        <div className="grid gap-2">
          <Label>Additional Instructions</Label>
          <Input
            value={instruction}
            onChange={(e) => setInstruction(e.target.value)}
            placeholder="e.g. These are German invoices from 2026"
            disabled={disabled}
          />
        </div>

        <Button
          onClick={handleSubmit}
          disabled={disabled || !convention.trim()}
          className="w-full"
        >
          <Sparkles className="mr-2 size-4" />
          Generate Preview
        </Button>
      </CardContent>
    </Card>
  )
}
