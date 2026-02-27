- To regenerate the JavaScript SDK, run `./packages/sdk/js/script/build.ts`.
- ALWAYS USE PARALLEL TOOLS WHEN APPLICABLE.
- The default branch in this repo is `dev`.
- Local `main` ref may not exist; use `dev` or `origin/dev` for diffs.
- Prefer automation: execute requested actions without confirmation unless blocked by missing info or safety/irreversibility.

## Style Guide

### General Principles

- Keep things in one function unless composable or reusable
- Avoid `try`/`catch` where possible
- Avoid using the `any` type
- Prefer single word variable names where possible
- Use Bun APIs when possible, like `Bun.file()`
- Rely on type inference when possible; avoid explicit type annotations or interfaces unless necessary for exports or clarity
- Prefer functional array methods (flatMap, filter, map) over for loops; use type guards on filter to maintain type inference downstream

### Naming

Prefer single word names for variables and functions. Only use multiple words if necessary.

```ts
// Good
const foo = 1
function journal(dir: string) {}

// Bad
const fooBar = 1
function prepareJournal(dir: string) {}
```

Reduce total variable count by inlining when a value is only used once.

```ts
// Good
const journal = await Bun.file(path.join(dir, "journal.json")).json()

// Bad
const journalPath = path.join(dir, "journal.json")
const journal = await Bun.file(journalPath).json()
```

### Destructuring

Avoid unnecessary destructuring. Use dot notation to preserve context.

```ts
// Good
obj.a
obj.b

// Bad
const { a, b } = obj
```

### Variables

Prefer `const` over `let`. Use ternaries or early returns instead of reassignment.

```ts
// Good
const foo = condition ? 1 : 2

// Bad
let foo
if (condition) foo = 1
else foo = 2
```

### Control Flow

Avoid `else` statements. Prefer early returns.

```ts
// Good
function foo() {
  if (condition) return 1
  return 2
}

// Bad
function foo() {
  if (condition) return 1
  else return 2
}
```

### Schema Definitions (Drizzle)

Use snake_case for field names so column names don't need to be redefined as strings.

```ts
// Good
const table = sqliteTable("session", {
  id: text().primaryKey(),
  project_id: text().notNull(),
  created_at: integer().notNull(),
})

// Bad
const table = sqliteTable("session", {
  id: text("id").primaryKey(),
  projectID: text("project_id").notNull(),
  createdAt: integer("created_at").notNull(),
})
```

## Testing

- Avoid mocks as much as possible
- Test actual implementation, do not duplicate logic into tests
- Tests cannot run from repo root (guard: `do-not-run-tests-from-root`); run from package dirs like `packages/opencode`.

---

## TISS Arena — Video Analysis Workflow

This is a fork of Opencode powering **TISS Arena**, a sports analytics desktop app. When the user attaches video frames or asks about video content, follow the two-phase workflow below.

### Phase 1: Visual Analysis (Look First)

Use your native vision capabilities to analyze any attached frames before taking action.

- **Describe what you see**: players, actions, formations, timestamps, scene changes, camera angles
- **Identify key moments**: goals, fouls, tackles, transitions, cuts, overlays
- **Note timecodes**: reference the frame timestamps provided by the UI (shown in `HH:MM:SS:FF` format)
- **Ask for more frames** if the provided ones don't cover the region of interest

### Phase 2: MCP Tool Execution (Act Second)

Only after visual analysis, use the appropriate MCP tool for the requested operation:

| Task | Tool | Example |
|------|------|---------|
| Trim/clip a segment | `ffmpeg-mcp` → `clip_video` | Clip from 00:01:23 to 00:02:45 |
| Extract frames | `ffmpeg-mcp` → `extract_frames` | Pull frames every 2 seconds |
| Get video info | `ffmpeg-mcp` → `get_media_info` | Duration, resolution, codec |
| Format conversion | `video-audio` → `convert_format` | MP4 → MOV |
| Add transitions | `video-audio` → `add_transition` | Fade between clips |
| Speed change | `video-audio` → `change_speed` | Slow-mo replay at 0.25x |
| Add subtitles | `video-audio` → `add_subtitles` | Overlay player names |
| Apply visual FX | `vidmagik` | Color grading, compositing, motion effects |
| Record narration | `audio-interface` | Record mic audio for voiceover |
| Browser research | `playwright` | Open tactical analysis sites |
| YouTube lookup | `youtube` | Search for match highlights |

### Rules

1. **Never guess timestamps** — always base them on analyzed frames or `get_media_info` output
2. **Always analyze frames first** — describe what you see before suggesting or executing edits
3. **Request more frames if needed** — if the user asks about a moment not covered by attached frames, ask them to seek to that point and send another frame
4. **Confirm destructive operations** — before overwriting source files, confirm with the user or write to a new output path
5. **Chain tools when needed** — e.g., extract frames → analyze → clip → apply effect
