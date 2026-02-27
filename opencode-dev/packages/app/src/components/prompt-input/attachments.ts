import { onCleanup, onMount } from "solid-js"
import { showToast } from "@opencode-ai/ui/toast"
import { usePrompt, type ContentPart, type ImageAttachmentPart } from "@/context/prompt"
import { useLanguage } from "@/context/language"
import { uuid } from "@/utils/uuid"
import { getCursorPosition } from "./editor-dom"

export const ACCEPTED_IMAGE_TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp"]
export const ACCEPTED_VIDEO_TYPES = ["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"]
export const ACCEPTED_FILE_TYPES = [...ACCEPTED_IMAGE_TYPES, ...ACCEPTED_VIDEO_TYPES, "application/pdf"]
const VIDEO_SIZE_THRESHOLD = 20 * 1024 * 1024 // 20MB
const LARGE_PASTE_CHARS = 8000
const LARGE_PASTE_BREAKS = 120

function largePaste(text: string) {
  if (text.length >= LARGE_PASTE_CHARS) return true
  let breaks = 0
  for (const char of text) {
    if (char !== "\n") continue
    breaks += 1
    if (breaks >= LARGE_PASTE_BREAKS) return true
  }
  return false
}

type PromptAttachmentsInput = {
  editor: () => HTMLDivElement | undefined
  isFocused: () => boolean
  isDialogActive: () => boolean
  setDraggingType: (type: "image" | "@mention" | null) => void
  focusEditor: () => void
  addPart: (part: ContentPart) => boolean
  readClipboardImage?: () => Promise<File | null>
}

export function createPromptAttachments(input: PromptAttachmentsInput) {
  const prompt = usePrompt()
  const language = useLanguage()

  const addVideoFrames = async (file: File) => {
    const url = URL.createObjectURL(file)
    try {
      const video = document.createElement("video")
      video.muted = true
      video.preload = "auto"
      video.src = url

      await new Promise<void>((resolve, reject) => {
        video.onloadedmetadata = () => resolve()
        video.onerror = () => reject(new Error("Failed to load video"))
      })

      if (!video.duration || !isFinite(video.duration)) return

      const canvas = document.createElement("canvas")
      const maxWidth = 1280
      const scale = video.videoWidth > maxWidth ? maxWidth / video.videoWidth : 1
      canvas.width = Math.round(video.videoWidth * scale)
      canvas.height = Math.round(video.videoHeight * scale)
      const ctx = canvas.getContext("2d")
      if (!ctx) return

      const frameCount = Math.min(16, Math.max(1, Math.ceil(video.duration / 10)))
      const frames: ImageAttachmentPart[] = []
      const baseName = file.name.replace(/\.[^.]+$/, "")

      for (let i = 0; i < frameCount; i++) {
        video.currentTime = (video.duration / frameCount) * (i + 0.5)
        await new Promise<void>((r) => {
          video.onseeked = () => r()
        })
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
        const dataUrl = canvas.toDataURL("image/jpeg", 0.7)
        const secs = Math.floor(video.currentTime)
        frames.push({
          type: "image",
          id: uuid(),
          filename: `${baseName}_frame_${String(i + 1).padStart(2, "0")}_${secs}s.jpg`,
          mime: "image/jpeg",
          dataUrl,
        })
      }

      if (frames.length === 0) return
      const editor = input.editor()
      if (!editor) return
      const cursorPosition = prompt.cursor() ?? getCursorPosition(editor)
      prompt.set([...prompt.current(), ...frames], cursorPosition)

      showToast({
        title: `Extracted ${frames.length} frames from video`,
        description: file.name,
      })
    } finally {
      URL.revokeObjectURL(url)
    }
  }

  const addImageAttachment = async (file: File) => {
    if (!ACCEPTED_FILE_TYPES.includes(file.type)) return

    // Large video files: extract frames instead of sending raw
    if (ACCEPTED_VIDEO_TYPES.includes(file.type) && file.size > VIDEO_SIZE_THRESHOLD) {
      await addVideoFrames(file)
      return
    }

    const reader = new FileReader()
    reader.onload = () => {
      const editor = input.editor()
      if (!editor) return
      const dataUrl = reader.result as string
      const attachment: ImageAttachmentPart = {
        type: "image",
        id: uuid(),
        filename: file.name,
        mime: file.type,
        dataUrl,
      }
      const cursorPosition = prompt.cursor() ?? getCursorPosition(editor)
      prompt.set([...prompt.current(), attachment], cursorPosition)
    }
    reader.readAsDataURL(file)
  }

  const removeImageAttachment = (id: string) => {
    const current = prompt.current()
    const next = current.filter((part) => part.type !== "image" || part.id !== id)
    prompt.set(next, prompt.cursor())
  }

  const handlePaste = async (event: ClipboardEvent) => {
    if (!input.isFocused()) return
    const clipboardData = event.clipboardData
    if (!clipboardData) return

    event.preventDefault()
    event.stopPropagation()

    const items = Array.from(clipboardData.items)
    const fileItems = items.filter((item) => item.kind === "file")
    const imageItems = fileItems.filter((item) => ACCEPTED_FILE_TYPES.includes(item.type))

    if (imageItems.length > 0) {
      for (const item of imageItems) {
        const file = item.getAsFile()
        if (file) await addImageAttachment(file)
      }
      return
    }

    if (fileItems.length > 0) {
      showToast({
        title: language.t("prompt.toast.pasteUnsupported.title"),
        description: language.t("prompt.toast.pasteUnsupported.description"),
      })
      return
    }

    const plainText = clipboardData.getData("text/plain") ?? ""

    // Desktop: Browser clipboard has no images and no text, try platform's native clipboard for images
    if (input.readClipboardImage && !plainText) {
      const file = await input.readClipboardImage()
      if (file) {
        await addImageAttachment(file)
        return
      }
    }

    if (!plainText) return

    if (largePaste(plainText)) {
      if (input.addPart({ type: "text", content: plainText, start: 0, end: 0 })) return
      input.focusEditor()
      if (input.addPart({ type: "text", content: plainText, start: 0, end: 0 })) return
    }

    const inserted = typeof document.execCommand === "function" && document.execCommand("insertText", false, plainText)
    if (inserted) return

    input.addPart({ type: "text", content: plainText, start: 0, end: 0 })
  }

  const handleGlobalDragOver = (event: DragEvent) => {
    if (input.isDialogActive()) return

    event.preventDefault()
    const hasFiles = event.dataTransfer?.types.includes("Files")
    const hasText = event.dataTransfer?.types.includes("text/plain")
    if (hasFiles) {
      input.setDraggingType("image")
    } else if (hasText) {
      input.setDraggingType("@mention")
    }
  }

  const handleGlobalDragLeave = (event: DragEvent) => {
    if (input.isDialogActive()) return
    if (!event.relatedTarget) {
      input.setDraggingType(null)
    }
  }

  const handleGlobalDrop = async (event: DragEvent) => {
    if (input.isDialogActive()) return

    event.preventDefault()
    input.setDraggingType(null)

    const plainText = event.dataTransfer?.getData("text/plain")
    const filePrefix = "file:"
    if (plainText?.startsWith(filePrefix)) {
      const filePath = plainText.slice(filePrefix.length)
      input.focusEditor()
      input.addPart({ type: "file", path: filePath, content: "@" + filePath, start: 0, end: 0 })
      return
    }

    const dropped = event.dataTransfer?.files
    if (!dropped) return

    for (const file of Array.from(dropped)) {
      if (ACCEPTED_FILE_TYPES.includes(file.type)) {
        await addImageAttachment(file)
      }
    }
  }

  onMount(() => {
    document.addEventListener("dragover", handleGlobalDragOver)
    document.addEventListener("dragleave", handleGlobalDragLeave)
    document.addEventListener("drop", handleGlobalDrop)
  })

  onCleanup(() => {
    document.removeEventListener("dragover", handleGlobalDragOver)
    document.removeEventListener("dragleave", handleGlobalDragLeave)
    document.removeEventListener("drop", handleGlobalDrop)
  })

  return {
    addImageAttachment,
    removeImageAttachment,
    handlePaste,
  }
}
