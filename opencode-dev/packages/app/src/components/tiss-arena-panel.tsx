import { For, Show, createMemo, createSignal, createEffect, on, onCleanup, batch } from "solid-js"
import { createResizeObserver } from "@solid-primitives/resize-observer"
import { convertFileSrc } from "@tauri-apps/api/core"

// Module-level caches survive re-mounts, avoid re-extraction
const thumbnailCache = new Map<string, string[]>()
const waveformCache = new Map<string, number[]>()

interface TissArenaPanelProps {
  videoPath?: string
  onClearVideo?: () => void
}

function formatTimecode(seconds: number, fps = 24): string {
  if (!isFinite(seconds) || seconds < 0) return "00:00:00:00"
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  const f = Math.floor((seconds % 1) * fps)
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}:${String(f).padStart(2, "0")}`
}

/**
 * TISS Arena - Live Analytics Feed & Media Tracks Panel
 * Center panel displaying video preview and timeline tracks
 */
export function TissArenaPanel(props: TissArenaPanelProps) {
  // State signals
  const [currentTime, setCurrentTime] = createSignal(0)
  const [duration, setDuration] = createSignal(0)
  const [isPlaying, setIsPlaying] = createSignal(false)
  const [thumbnails, setThumbnails] = createSignal<string[]>([])
  const [waveformPeaks, setWaveformPeaks] = createSignal<number[]>([])
  const [isSeeking, setIsSeeking] = createSignal(false)
  const [trackWidth, setTrackWidth] = createSignal(600)

  // Refs
  let videoRef: HTMLVideoElement | undefined
  let trackContainerRef: HTMLDivElement | undefined

  const videoSrc = createMemo(() => {
    const path = props.videoPath
    if (!path) return undefined
    return convertFileSrc(path)
  })

  const videoFileName = createMemo(() => {
    const path = props.videoPath
    if (!path) return undefined
    const sep = path.lastIndexOf("/") !== -1 ? "/" : "\\"
    return path.slice(path.lastIndexOf(sep) + 1)
  })

  // Timecode displays
  const timecodeDisplay = createMemo(() => formatTimecode(currentTime()))
  const durationDisplay = createMemo(() => formatTimecode(duration()))

  // Playhead position as percentage
  const playheadPercent = createMemo(() => {
    const d = duration()
    return d > 0 ? (currentTime() / d) * 100 : 0
  })

  // Thumbnail count based on track width (~80px per thumb), capped at 30 to avoid OOM on long videos
  const thumbnailCount = createMemo(() => Math.min(30, Math.max(1, Math.floor(trackWidth() / 80))))

  // Video ref callback - attach event listeners
  const setVideoRef = (el: HTMLVideoElement) => {
    videoRef = el
    el.addEventListener("loadedmetadata", () => setDuration(el.duration))
    el.addEventListener("timeupdate", () => {
      if (!isSeeking()) setCurrentTime(el.currentTime)
    })
    el.addEventListener("play", () => setIsPlaying(true))
    el.addEventListener("pause", () => setIsPlaying(false))
    el.addEventListener("ended", () => setIsPlaying(false))
  }

  // Reset signals when video changes
  createEffect(on(() => props.videoPath, () => {
    batch(() => {
      setCurrentTime(0)
      setDuration(0)
      setIsPlaying(false)
      setThumbnails([])
      setWaveformPeaks([])
    })
  }, { defer: true }))

  // Smooth playhead animation via rAF when playing
  createEffect(() => {
    if (!isPlaying()) return
    let rafId: number
    const tick = () => {
      if (videoRef && !isSeeking()) setCurrentTime(videoRef.currentTime)
      rafId = requestAnimationFrame(tick)
    }
    rafId = requestAnimationFrame(tick)
    onCleanup(() => cancelAnimationFrame(rafId))
  })

  // Click/drag seeking on timeline
  const seekToPosition = (clientX: number) => {
    if (!trackContainerRef || !videoRef || duration() <= 0) return
    const rect = trackContainerRef.getBoundingClientRect()
    const fraction = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width))
    videoRef.currentTime = fraction * duration()
    setCurrentTime(videoRef.currentTime)
  }

  const onTrackMouseDown = (e: MouseEvent) => {
    if (e.button !== 0) return
    e.preventDefault()
    setIsSeeking(true)
    seekToPosition(e.clientX)

    const onMove = (ev: MouseEvent) => seekToPosition(ev.clientX)
    const onUp = () => {
      setIsSeeking(false)
      document.removeEventListener("mousemove", onMove)
      document.removeEventListener("mouseup", onUp)
    }
    document.addEventListener("mousemove", onMove)
    document.addEventListener("mouseup", onUp)
  }

  // Thumbnail extraction
  createEffect(on(videoSrc, (src) => {
    if (!src) return
    const path = props.videoPath!
    const cached = thumbnailCache.get(path)
    if (cached) { setThumbnails(cached); return }
    extractThumbnails(src, path)
  }))

  async function extractThumbnails(src: string, originalPath: string) {
    const video = document.createElement("video")
    const canvas = document.createElement("canvas")
    video.muted = true
    video.src = src

    try {
      await new Promise<void>((resolve, reject) => {
        video.onloadedmetadata = () => resolve()
        video.onerror = () => reject()
      })
    } catch { return }

    if (props.videoPath !== originalPath) return
    if (!video.duration || !isFinite(video.duration)) return

    const count = thumbnailCount()
    const ctx = canvas.getContext("2d")
    if (!ctx) return

    canvas.width = 160
    canvas.height = 90
    const results: string[] = []

    for (let i = 0; i < count; i++) {
      if (props.videoPath !== originalPath) return

      video.currentTime = (video.duration / count) * (i + 0.5)
      await new Promise<void>(r => { video.onseeked = () => r() })

      if (props.videoPath !== originalPath) return
      ctx.drawImage(video, 0, 0, 160, 90)
      results.push(canvas.toDataURL("image/jpeg", 0.6))
    }

    thumbnailCache.set(originalPath, results)
    if (props.videoPath === originalPath) setThumbnails(results)
  }

  // Waveform extraction
  createEffect(on(videoSrc, (src) => {
    if (!src) return
    const path = props.videoPath!
    const cached = waveformCache.get(path)
    if (cached) { setWaveformPeaks(cached); return }
    extractWaveform(src, path)
  }))

  async function extractWaveform(src: string, originalPath: string) {
    // Limit: only fetch first 50MB to avoid OOM on large videos
    const MAX_BYTES = 50 * 1024 * 1024
    try {
      const resp = await fetch(src, { headers: { Range: "bytes=0-" + (MAX_BYTES - 1) } })
      if (props.videoPath !== originalPath) return

      const buf = await resp.arrayBuffer()
      if (props.videoPath !== originalPath) return

      // Skip if the fetched chunk is too small to contain audio
      if (buf.byteLength < 1024) return

      const audioCtx = new AudioContext()
      let audioBuffer: AudioBuffer
      try {
        audioBuffer = await audioCtx.decodeAudioData(buf)
      } catch {
        await audioCtx.close()
        return // No audio track or partial data not decodable
      }
      await audioCtx.close()

      if (props.videoPath !== originalPath) return

      const data = audioBuffer.getChannelData(0)
      const peakCount = 200
      const blockSize = Math.floor(data.length / peakCount)
      const peaks: number[] = []
      let maxPeak = 0

      for (let i = 0; i < peakCount; i++) {
        let sum = 0
        const start = i * blockSize
        for (let j = start; j < start + blockSize && j < data.length; j++) {
          sum += Math.abs(data[j])
        }
        const avg = blockSize > 0 ? sum / blockSize : 0
        peaks.push(avg)
        if (avg > maxPeak) maxPeak = avg
      }

      const normalized = maxPeak > 0 ? peaks.map(p => p / maxPeak) : peaks
      waveformCache.set(originalPath, normalized)
      if (props.videoPath === originalPath) setWaveformPeaks(normalized)
    } catch {
      // Fetch error or no audio — waveform stays empty
    }
  }

  return (
    <section class="flex-1 flex flex-col p-4 bg-background-base min-w-0">
      <div class="flex-1 border border-[#8B5CF6] rounded-xl overflow-hidden flex flex-col shadow-[0_0_20px_rgba(139,92,246,0.15)] relative">

        {/* Top Half: Video Player Area */}
        <div class="flex-1 bg-background-stronger relative flex items-center justify-center overflow-hidden">
          {/* "Live Analytics Feed" badge */}
          <div class="absolute top-4 left-4 z-10">
            <div class="bg-background-base/80 border border-[#84cc16]/30 rounded px-2 py-1 flex items-center gap-2">
              <div class="w-1.5 h-1.5 rounded-full bg-[#84cc16] animate-pulse shadow-[0_0_5px_#84cc16]" />
              <span class="text-[10px] font-mono text-[#84cc16] font-bold tracking-widest">LIVE ANALYTICS FEED</span>
            </div>
          </div>

          <Show
            when={videoSrc()}
            fallback={
              <div class="flex flex-col items-center text-text-weak opacity-30">
                <svg width="80" height="80" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round">
                  <path d="m16 13 5.223 3.482a.5.5 0 0 0 .777-.416V7.87a.5.5 0 0 0-.752-.432L16 10.5" />
                  <rect x="2" y="6" width="14" height="12" rx="2" />
                </svg>
                <div class="mt-6 text-sm font-mono tracking-widest opacity-80 uppercase text-text-weak">
                  Previewing: Left-foot strike from outside the box
                </div>
              </div>
            }
          >
            {(src) => (
              <>
                <video
                  src={src()}
                  ref={setVideoRef}
                  controls
                  autoplay
                  class="w-full h-full object-contain bg-black"
                />
                {/* Filename badge + close button */}
                <div class="absolute top-4 right-4 z-10 flex items-center gap-2">
                  <div class="bg-background-base/80 border border-border-weak rounded px-2 py-1">
                    <span class="text-[10px] font-mono text-text-base truncate max-w-48 inline-block">{videoFileName()}</span>
                  </div>
                  <button
                    class="bg-background-base/80 border border-border-weak rounded w-6 h-6 flex items-center justify-center hover:bg-background-base cursor-pointer"
                    onClick={() => props.onClearVideo?.()}
                    title="Close video"
                  >
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-text-weak">
                      <path d="M18 6 6 18" />
                      <path d="m6 6 12 12" />
                    </svg>
                  </button>
                </div>
              </>
            )}
          </Show>
        </div>

        {/* Bottom Half: Media Tracks Timeline */}
        <div class="h-44 bg-background-base border-t border-[#8B5CF6]/30 flex flex-col shrink-0">
          {/* Timeline Header */}
          <div class="h-10 px-4 flex items-center justify-between border-b border-border-weak">
            <div class="flex items-center gap-4">
              <div class="flex items-center gap-2 bg-background-stronger px-2 py-1 rounded border border-border-weak">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#84cc16" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2" />
                </svg>
                <span class="text-[10px] font-bold text-text-base uppercase tracking-widest">Media Tracks</span>
              </div>
              <div class="h-3 w-px bg-border-weak" />
              <span class="font-mono text-[11px] text-[#84cc16]">
                {timecodeDisplay()}
                <Show when={duration() > 0}>
                  <span class="text-text-weak"> / {durationDisplay()}</span>
                </Show>
              </span>
            </div>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-text-weak cursor-pointer hover:text-text-base">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
              <circle cx="12" cy="12" r="3" />
            </svg>
          </div>

          {/* Tracks Area */}
          <div class="flex-1 flex relative overflow-hidden">
            {/* Track Headers (Left Column) */}
            <div class="w-14 flex flex-col border-r border-border-weak bg-background-base shrink-0 z-10">
              <div class="flex-1 flex flex-col items-center justify-center border-b border-border-weak gap-1">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-text-weak">
                  <rect width="18" height="18" x="3" y="3" rx="2" />
                  <path d="m10 8 6 4-6 4Z" />
                </svg>
                <span class="text-[9px] font-bold text-text-weak">V1</span>
              </div>
              <div class="flex-1 flex flex-col items-center justify-center gap-1">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-text-weak">
                  <path d="M11 4.702a.705.705 0 0 0-1.203-.498L6.413 7.587A1.4 1.4 0 0 1 5.416 8H3a1 1 0 0 0-1 1v6a1 1 0 0 0 1 1h2.416a1.4 1.4 0 0 1 .997.413l3.383 3.384A.705.705 0 0 0 11 19.298z" />
                  <path d="M16 9a5 5 0 0 1 0 6" />
                  <path d="M19.364 18.364a9 9 0 0 0 0-12.728" />
                </svg>
                <span class="text-[9px] font-bold text-text-weak">A1</span>
              </div>
            </div>

            {/* Tracks Content (seekable area) */}
            <div
              ref={(el) => {
                trackContainerRef = el
                createResizeObserver(el, (rect) => {
                  if (rect.width > 0) setTrackWidth(rect.width)
                })
              }}
              class="flex-1 flex flex-col relative overflow-hidden select-none"
              onMouseDown={onTrackMouseDown}
            >
              {/* Playhead */}
              <div
                class="absolute inset-y-0 w-px bg-white z-20 shadow-[0_0_8px_rgba(255,255,255,0.8)] pointer-events-none"
                style={{ left: `${playheadPercent()}%` }}
              >
                <div class="absolute -top-1 left-1/2 -translate-x-1/2 w-2.5 h-2.5 bg-white rounded-full shadow-[0_0_5px_white]" />
              </div>

              {/* Grid Lines Overlay */}
              <div class="absolute inset-0 flex pointer-events-none">
                <For each={Array.from({ length: 10 })}>
                  {() => <div class="flex-1 border-r border-border-weak/50 h-full" />}
                </For>
              </div>

              {/* V1 Track */}
              <div class="flex-1 border-b border-border-weak flex items-stretch relative overflow-hidden">
                <Show
                  when={thumbnails().length > 0}
                  fallback={
                    <Show when={videoSrc()}>
                      <div class="flex items-center justify-center w-full">
                        <span class="text-[10px] text-text-weak font-mono animate-pulse">Extracting frames...</span>
                      </div>
                    </Show>
                  }
                >
                  <div class="flex w-full h-full">
                    <For each={thumbnails()}>
                      {(thumb) => (
                        <img
                          src={thumb}
                          class="flex-1 object-cover h-full min-w-0 opacity-80"
                          draggable={false}
                        />
                      )}
                    </For>
                  </div>
                </Show>
              </div>

              {/* A1 Track */}
              <div class="flex-1 flex items-center relative px-1">
                <Show
                  when={waveformPeaks().length > 0}
                  fallback={
                    <Show when={videoSrc()}>
                      <div class="flex items-center justify-center w-full">
                        <span class="text-[10px] text-text-weak font-mono animate-pulse">Analyzing audio...</span>
                      </div>
                    </Show>
                  }
                >
                  <div class="w-full h-full flex items-center gap-[1px]">
                    <For each={waveformPeaks()}>
                      {(peak) => (
                        <div class="flex-1 bg-[#0D9488]/60" style={{ height: `${peak * 100}%` }} />
                      )}
                    </For>
                  </div>
                </Show>
                {/* Centered waveform line */}
                <div class="absolute inset-x-0 top-1/2 h-px bg-[#0D9488]/80 pointer-events-none" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
