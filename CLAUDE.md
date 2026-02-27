# TISS Arena - Project Instructions

## Project Overview
TISS Arena is a sports analytics desktop application built on top of Opencode (an AI-powered development tool). It runs as a Tauri desktop app with a SolidJS frontend. The project lives inside a fork/clone of the Opencode monorepo.

## Directory Structure
```
D:\TISS_Arena\
├── opencode-dev/                    # Opencode monorepo (Tauri + SolidJS + Bun)
│   ├── packages/
│   │   ├── app/                     # SolidJS frontend (main UI)
│   │   │   └── src/components/
│   │   │       └── tiss-arena-panel.tsx   # Center panel: video player + media tracks
│   │   ├── desktop/                 # Tauri desktop shell (Rust backend)
│   │   │   └── src-tauri/
│   │   ├── opencode/                # Core opencode CLI/server
│   │   └── sdk/                     # SDK packages
│   ├── .opencode/
│   │   └── opencode.jsonc           # Project-level opencode config (keep mcp: {} empty)
│   └── package.json                 # Root monorepo scripts
├── MCP_Servers_repos/               # MCP server source code
│   ├── Audio-MCP-Server-main/       # Python - mic recording/playback
│   ├── ffmpeg-mcp-main (1)/         # Python - FFmpeg video operations
│   │   └── ffmpeg-mcp-main/
│   ├── playwright-mcp-main/         # Node.js - browser automation (Microsoft)
│   ├── video-audio-mcp-main/        # Python - 27+ editing tools
│   ├── vidmagik-mcp-main/           # Python - 70+ MoviePy effects (needs --transport stdio)
│   └── youtube-mcp-server-main/     # TypeScript - YouTube API
└── CLAUDE.md                        # This file
```

## How to Run
```bash
cd D:/TISS_Arena/opencode-dev
bun run dev:desktop        # Full Tauri desktop app (compiles Rust + Vite)
bun run dev:web            # Web-only frontend (Vite dev server on :1420)
```

## Key Technologies
- **Runtime**: Bun 1.3.10 (package manager + script runner)
- **Frontend**: SolidJS 1.9, TailwindCSS 4.x, Vite 7.x
- **Desktop**: Tauri 2.x (Rust backend)
- **Language**: TypeScript (strict mode, JSX preserve, jsxImportSource: solid-js)
- **Video**: Tauri asset protocol via `convertFileSrc()` from `@tauri-apps/api/core`

## Configuration Files
| File | Purpose |
|------|---------|
| `~/.config/opencode/opencode.jsonc` | **Global MCP server config** (this is where MCP servers are registered) |
| `opencode-dev/.opencode/opencode.jsonc` | Project-level config (keep `mcp: {}` empty, global config handles servers) |
| `opencode-dev/packages/app/tsconfig.json` | App TypeScript config (composite, strict, solid-js JSX) |

---

## Feature: Functional Media Tracks Timeline

### File: `packages/app/src/components/tiss-arena-panel.tsx`

### What It Does
The center panel of TISS Arena with a video player (top half) and an interactive media timeline (bottom half). The timeline has:
- **V1 Track**: Video thumbnail filmstrip extracted from the loaded video
- **A1 Track**: Real audio waveform visualization
- **Playhead**: Synced to `<video>` element, moves smoothly at ~60fps via rAF
- **Timecode**: Live `HH:MM:SS:FF` display (24fps) with duration
- **Seeking**: Click or drag anywhere on the timeline to scrub through video

### Architecture
```
Imports: solid-js (createSignal, createEffect, on, onCleanup, batch, For, Show, createMemo)
         @solid-primitives/resize-observer (createResizeObserver)
         @tauri-apps/api/core (convertFileSrc)

Module-level caches (survive re-mounts):
  thumbnailCache: Map<string, string[]>    — extracted JPEG data URLs per video path
  waveformCache: Map<string, number[]>     — normalized 0..1 peak values per video path

Signals: currentTime, duration, isPlaying, thumbnails, waveformPeaks, isSeeking, trackWidth
Refs: videoRef (main <video>), trackContainerRef (seekable area)
```

### How Thumbnail Extraction Works
1. Creates offscreen `document.createElement("video")` + `<canvas>` (not in DOM)
2. Sets video src to Tauri asset URL, waits for `loadedmetadata`
3. Calculates thumbnail count from track width (~80px per thumb)
4. Seeks to evenly-spaced positions, draws frame to canvas, calls `toDataURL("image/jpeg", 0.6)`
5. Caches results by video path; aborts if `props.videoPath` changes mid-extraction

### How Waveform Extraction Works
1. `fetch(src)` the video as ArrayBuffer
2. `new AudioContext().decodeAudioData(buffer)` to get audio samples
3. Divides channel data into 200 blocks, computes average absolute amplitude per block
4. Normalizes to 0..1 range, caches by path
5. Gracefully catches `decodeAudioData` errors (videos with no audio track)

### How Seeking Works
1. `onMouseDown` on tracks content container sets `isSeeking(true)` and seeks to click position
2. Registers `mousemove`/`mouseup` on `document` for drag-to-scrub
3. `seekToPosition(clientX)` computes fraction from container bounds, sets `videoRef.currentTime`
4. `isSeeking` flag prevents `timeupdate` events from fighting with manual position updates

### Edge Cases Handled
- No video loaded: timeline stays empty, playhead at 0%
- No audio track: `decodeAudioData` throws, caught gracefully, A1 track stays empty
- Rapid video switching: checks `props.videoPath !== originalPath` after every `await`
- Very short video: `Math.max(1, ...)` ensures at least 1 thumbnail

---

## MCP Servers Setup

### Global Config Location
`~/.config/opencode/opencode.jsonc` (also mirrors to `%APPDATA%/opencode/opencode.jsonc`)

### Registered Servers

| Server Name | Language | Entry Point | Tools |
|-------------|----------|-------------|-------|
| `audio-interface` | Python | `Audio-MCP-Server-main/audio_server.py` | 5: list devices, record, play, play file |
| `ffmpeg-mcp` | Python | `ffmpeg-mcp-main/src/ffmpeg_mcp/server.py` | 8: find, info, clip, concat, play, overlay, scale, extract frames |
| `video-audio` | Python | `video-audio-mcp-main/server.py` | 27+: format conversion, trim, transitions, subtitles, speed, silence removal |
| `vidmagik` | Python | `vidmagik-mcp-main/main.py --transport stdio` | 70+: MoviePy compositing, color, geometry, motion, custom FX (matrix, kaleidoscope, chroma key) |
| `playwright` | Node.js | `playwright-mcp-main/packages/playwright-mcp/cli.js` | Browser automation: navigate, click, fill, screenshot, PDF, accessibility snapshots |
| `youtube` | Node.js | `youtube-mcp-server-main/dist/index.js` | 7: search, video info, transcripts, channels, playlists |

### Python Dependencies (installed globally in Python 3.12)
```
sounddevice, soundfile, numpy, ffmpeg-python, moviepy, numexpr,
opencv-contrib-python-headless, fastmcp>=3.0.0, mcp, pillow
```

### Playwright MCP Setup
```bash
cd D:/TISS_Arena/MCP_Servers_repos/playwright-mcp-main
npm install
```
No env vars needed. Uses Chromium by default.

### YouTube Server Setup
```bash
cd D:/TISS_Arena/MCP_Servers_repos/youtube-mcp-server-main
npm install
npm run build    # Compiles TypeScript to dist/
```
Requires `YOUTUBE_API_KEY` environment variable (set in opencode.jsonc config).

### VidMagik Note
VidMagik defaults to HTTP transport. Must pass `--transport stdio` in the command array for Opencode compatibility.

### MCP Config Format (for adding new servers)
```jsonc
{
  "server-name": {
    "type": "local",
    "command": ["python", "D:/path/to/server.py"],
    "environment": {
      "PYTHONPATH": "D:/path/to/server/directory",
      "SOME_API_KEY": "value"
    },
    "enabled": true
  }
}
```

### How Opencode Loads MCP Tools
1. Reads `mcp` section from config (global + project merged)
2. Spawns each server via `StdioClientTransport` (local) or HTTP/SSE (remote)
3. Calls `MCP.tools()` to discover available tools
4. Tools are named `{serverName}_{toolName}` in the AI session
5. Server status visible in Opencode UI under the "MCP" tab

### Troubleshooting MCP Servers
- **Red dot** = server failed to connect. Check: command path exists, dependencies installed, env vars set
- **Placeholder values** (`YOUR_*`) = replace with real credentials or set `"enabled": false`
- **Test a Python server**: `cd <server_dir> && python -c "import <module>; print('OK')"`
- **Test YouTube server**: `YOUTUBE_API_KEY=test node dist/index.js` (should print "started successfully")
- **View logs**: MCP errors appear in the Tauri sidecar output during `bun run dev:desktop`

---

## Development Notes
- TypeScript checks: `bun run --workspace=packages/app typecheck` (uses `tsgo`)
- Pre-existing typecheck error in `custom-elements.d.ts` is a known issue (broken path reference)
- `@tauri-apps/api/core` import only resolves when building through Tauri pipeline, not standalone vite build
- SolidJS `<Show>` with callback children `{(accessor) => ...}` does NOT recreate children when the accessor value changes (only when truthiness flips). The `<video>` element is reused across src changes.
- `createResizeObserver` from `@solid-primitives/resize-observer` v2.1.3 signature: `createResizeObserver(target, (rect, element, entry) => void)`
