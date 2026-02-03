You are a senior full stack engineer. Build a local, packaged Windows desktop app that scans a local or external hard drive and helps organize media files (ebooks, audiobooks, comics, movies) using a review queue, metadata enrichment, consistent naming templates, a dry-run plan, safe apply, and rollback.

Hard constraints
- Must run fully locally on Windows 11 as a packaged desktop app.
- Must support scanning folders on an external drive letter like E:\ and local drives.
- Must work offline except for optional metadata provider calls.
- Must be safe by default: never move or rename without a dry-run plan and explicit user approval.
- Must include an audit log and rollback capability.
- Must minimize LLM and provider calls with aggressive caching and batching.
- Target scale is under 1 TB, optimize for correctness and safety over extreme performance.

Preferred architecture
- Desktop shell: Tauri v2
- UI: React + TypeScript (Vite)
- Backend: Python FastAPI packaged as a local executable and launched as a sidecar process by Tauri
- Local database: SQLite
- Jobs: simple background worker threads inside the FastAPI process for scan and apply

Deliverables
1) A working monorepo with:
   - Tauri desktop app, React UI
   - FastAPI backend
   - SQLite schema and migrations
   - A safe file operation engine: plan generation, apply, rollback
   - Provider integration modules with caching
   - Optional Gemini helper module with strict JSON schemas and caching
2) A complete README.md that:
   - Explains the wireframe pages and workflow
   - Explains safety model, dry run, apply, rollback
   - Explains configuration for Google Books, TMDb, and optional Gemini
   - Explains build steps to create a Windows installer or executable
   - Includes screenshots placeholders and suggested UI layout

Key product behavior
- User selects one or more root folders to scan.
- App catalogs files into SQLite with stable identity via sha256 hashing.
- App detects media types by extension.
- App extracts embedded metadata when available:
  - EPUB: parse OPF from ZIP
  - Audio: read tags for MP3 and M4B
  - CBZ: read ComicInfo.xml if present
  - Video: basic filename parsing only for MVP
- App generates candidate metadata and proposed target paths.
- App presents a Review Queue with:
  - current path, proposed title, author, year, type, confidence, proposed target path
  - per-item edit and provider search
  - approve or defer
- App generates an Apply Plan for approved items only.
- App shows a Plan Diff view that lists all renames and moves, flags collisions and duplicates.
- App applies operations only after the user clicks Apply Plan.
- App supports rollback per plan.

Provider integrations
Implement provider modules and caching in SQLite:
- Books: Google Books API and Open Library fallback
- Movies: TMDb API
Optional later:
- Comics: Comic Vine
Rules:
- Always cache provider responses by provider + query key.
- Always dedupe queries before calling providers.
- Always prefer identifier searches if found, like ISBN.

Optional LLM integration
- Add an optional Gemini Flash helper for:
  A) parsing messy filenames into structured guesses and search queries
  B) choosing best match among top provider results
Rules:
- Never send file contents.
- Only send short strings, filename, folders, small extracted tag fields.
- Batch parse calls, 50 to 200 items per request.
- Cache LLM output by file hash + prompt version + function name.
- Feature flag to disable LLM completely.
- Enforce strict JSON schema, validate, retry once on invalid JSON.

Safety model
- Default mode is Dry Run only.
- Apply operations must follow:
  - Validate file still exists and hash matches catalog entry.
  - If same volume, use atomic rename or move.
  - If different volume, copy then verify hash then delete original.
- Never overwrite existing files. If collision occurs, suffix the file name.
- Rollback reverses successful operations in reverse order.
- All operations are logged with plan id, timestamps, before and after paths.

Repository layout
media-organizer/
  backend/
    app/
      main.py
      db/
      media/
      providers/
      llm/
      ops/
      jobs/
      tests/
    requirements.txt
    pyproject.toml
    build_backend_exe.ps1
  frontend/
    src/
    package.json
    vite.config.ts
  desktop/
    src-tauri/
    tauri.conf.json
  README.md
  .env.example
  docker-not-used.md

Packaging approach
- Package FastAPI backend into a single Windows executable using PyInstaller.
- Tauri bundles the backend exe as a resource and launches it on app start, then shuts it down on app exit.
- The UI talks to backend over localhost on a fixed port with health checks and retry.

Implementation plan
Phase 1: Backend foundation
- Create FastAPI app with:
  - /health
  - /settings read and write, stored in SQLite
  - /scan/start, /scan/status
  - /files list with filters: type, status
  - /files/{id} get
  - /files/{id}/decision approve, update final metadata fields
  - /plan/generate create a plan for approved items
  - /plan/{plan_id} get details
  - /plan/{plan_id}/apply apply operations
  - /plan/{plan_id}/rollback rollback operations
- Create SQLite schema and minimal migrations.
- Add background job runner for scan and apply.

Phase 2: Scanner
- Implement recursive scan of selected roots.
- Exclusions for folders and patterns.
- Compute sha256 streaming and store in media_files.
- Detect type by extension.

Phase 3: Extraction and heuristics
- Add extractors for EPUB OPF, audio tags, CBZ ComicInfo.xml.
- Add filename parsing heuristics:
  - Title (Year)
  - Author - Title
  - Series patterns for audiobooks and comics as best effort

Phase 4: Rules engine and plan generator
- Add per-type templates for folder and filename.
- Add normalization rules for Windows filenames.
- Generate proposed target path for each approved decision.
- Detect collisions and duplicates by sha256.
- Produce plan summary and planned_operations rows.

Phase 5: Apply and rollback
- Implement safe apply, atomic rename on same volume, copy verify delete across volumes.
- Store operation status, errors, and rollback data.
- Implement rollback.

Phase 6: Providers and caching
- Add Google Books and Open Library modules.
- Add TMDb module.
- Add provider_cache table and caching layer.
- Add /files/{id}/search endpoint and UI search flow.

Phase 7: Optional Gemini helper
- Add llm helper module with strict JSON schema and caching.
- Add batch parse endpoint used by scan pipeline, optional.
- Add choose best candidate endpoint used by file detail screen, optional.

Phase 8: Desktop UI and packaging
- Build Tauri app that starts backend sidecar and renders React UI.
- Implement UI pages:
  - Dashboard
  - Scan Setup
  - Review Queue
  - File Detail Editor
  - Rules Editor
  - Plans and Plan Detail
  - Settings

Acceptance criteria
- App can scan a folder on an external drive letter and index files.
- Review Queue shows items, user can edit metadata, approve, generate plan.
- Plan shows diffs and can apply safely.
- Rollback restores original paths for applied items.
- Provider calls are cached, repeat searches do not call again.
- The packaged app runs on a Windows machine without Python installed.

Start now
- Generate the full repo with all files, code, and configuration.
- Keep code clean, typed, and modular.
- Provide sensible defaults and a .env.example.
- Include a sample folder in tests fixtures and integration tests that operate on a temporary directory.

Important implementation details
- Use pathlib for Windows paths.
- Avoid long path issues by enabling long path support in docs and using Windows-safe path handling.
- Ensure the backend binds to 127.0.0.1 only.
- Use CORS to allow the local UI origin.
- Include a health check loop in Tauri to wait for backend readiness before UI calls.

Proceed to implement.
# Media Organizer Desktop (Windows)

## What this is
A local-first Windows desktop app that scans a local or external drive and helps you organize mixed media files (ebooks, audiobooks, comics, movies) into a clean folder structure with consistent naming and metadata.

Core workflow:
1. Scan folders into a local catalog
2. Review and fix metadata in a queue
3. Generate a dry-run plan of moves and renames
4. Apply changes safely
5. Roll back a plan if needed

This is designed for under 1 TB libraries, prioritizing safety and correctness.

---

## Features

### Catalog and scan
- Scan one or more root folders
- Supports local drives and external drives like `E:\Media`
- Detects media type by file extension
- Computes SHA-256 per file for stable identity and duplicate detection
- Stores everything in a local SQLite database

### Metadata extraction
Best-effort, local extraction:
- EPUB: reads OPF metadata from the EPUB container
- Audio: reads tags for MP3 and M4B
- CBZ: reads ComicInfo.xml if present
- Video: filename parsing only in MVP

### Review Queue
A single place to validate and fix your library before any changes occur.
- Shows current path, proposed metadata, confidence, and proposed target path
- Supports per-item editing
- Supports provider search to find a better match
- Only approved items can be included in an apply plan

### Naming rules and folder templates
Configurable templates per media type, with previews.
- Books
- Audiobooks
- Comics
- Movies

Normalization rules for Windows-safe filenames:
- Remove illegal filename characters
- Collapse repeated spaces
- Standardize punctuation
- Handle collisions with safe suffixing

### Plans, apply, and rollback
- Generate a plan that contains all proposed operations
- See a plan diff view before applying
- Apply operations with safety checks:
  - Verify the file still exists
  - Verify hash matches the catalog
  - Same volume operations use atomic rename or move
  - Cross volume operations use copy, verify, delete
- Roll back an applied plan

### Provider integrations
Optional metadata enrichment with caching:
- Google Books for books and audiobook matching
- Open Library fallback for books
- TMDb for movies

All provider responses are cached in SQLite. Repeat queries should not call the provider again.

### Optional Gemini helper
Optional small-footprint LLM usage for:
- Parsing messy filenames into structured guesses and search queries
- Selecting the best match among top provider results

Rules:
- Never send file contents
- Only send short strings and small metadata snippets
- Batch requests and cache results per file hash

---

## Wireframe and pages

### Dashboard
- Scan status
- Counts by media type
- Counts needing review
- Recent plans and apply status

### Scan Setup
- Select root folders
- Exclusions
- Dry run mode and safety options
- Start scan

### Review Queue
Table view with filters
- Type
- Status
- Confidence threshold

Bulk actions
- Approve selected
- Defer selected

### File Detail
- Current path and detected type
- Extracted metadata sources and raw values
- Editable final metadata fields
- Provider search results list with “set as match”
- Approve toggle

### Rules
- Template editor per media type
- Normalization settings
- Live preview for sample metadata

### Plans
- Plans list with status
- Plan detail shows:
  - all proposed moves and renames
  - collision warnings
  - duplicates
  - Apply button
  - Rollback button

### Settings
- Provider keys
- LLM enablement
- Batch sizes and cache controls
- Advanced safety settings

---

## Architecture

### Desktop shell
- Tauri v2
- Launches a bundled backend executable on startup
- UI communicates with backend over localhost

### UI
- React + TypeScript
- Vite build
- Calls FastAPI endpoints

### Backend
- FastAPI
- SQLite database
- Background jobs for scan and apply tasks

---

## Repository layout

media-organizer/
backend/
app/
api/ FastAPI routes
core/ config, settings, helpers
db/ sqlite access, schema, migrations
media/ type detection, extractors, parsing
providers/ google books, open library, tmdb
llm/ optional gemini helpers
ops/ plan generator, executor, rollback
jobs/ scan and apply workers
tests/ unit and integration tests
build_backend_exe.ps1
requirements.txt
pyproject.toml
frontend/
src/
desktop/
src-tauri/
README.md
.env.example


---

## Setup for development

### Prerequisites
- Node.js 18 or newer
- Python 3.11 or newer
- Rust toolchain for Tauri
- Windows build tools as required by Tauri

### Environment configuration
Copy `.env.example` to `.env` in the repo root and fill in what you need.

Expected keys:
- GOOGLE_BOOKS_API_KEY
- TMDB_API_KEY
- GEMINI_API_KEY optional

Provider keys are optional, the app works without them, but metadata enrichment is reduced.

### Run backend
From `backend/`:
- create venv
- install requirements
- run FastAPI

The backend should bind to 127.0.0.1 only.

### Run frontend
From `frontend/`:
- install packages
- start dev server

### Run desktop
From `desktop/`:
- run Tauri dev

The desktop app should start the backend sidecar automatically.

---

## Packaging for Windows

### Build backend exe
The backend is packaged into a single Windows executable using PyInstaller.

The build script:
- `backend/build_backend_exe.ps1`

Output:
- `backend/dist/media_organizer_backend.exe`

### Bundle into Tauri
Tauri config includes the backend exe as a resource and launches it on app start.

The UI waits for backend `/health` to be ready before making calls.

### Build desktop installer or exe
Use Tauri build command to produce the Windows build artifacts.

---

## Safety and data integrity

### Default behavior
- The app does not rename or move anything during scan.
- The app only applies changes through an explicit plan.
- Plans are always previewable before apply.

### Hash validation
Before applying any operation, the backend verifies:
- The file exists
- The SHA-256 matches what was cataloged

### Cross-volume operations
If a move crosses volumes:
- copy file
- verify hash
- delete original

### Collisions
The executor never overwrites. It appends a safe suffix when needed.

### Rollback
Rollback reverses all successful operations in reverse order. It does not overwrite existing files during rollback. Conflicts are flagged for manual resolution.

---

## Default naming templates

These are defaults and can be edited in the Rules page.

Books
- Folder: `Books/{author_sort}/{title} ({year})`
- File: `{title} ({year}) - {author_sort}.{ext}`

Audiobooks
- Folder: `Audiobooks/{author_sort}/{series}/{series_index} - {title} ({year})`
- File: `{series_index} - {title} ({year}).{ext}`

Comics
- Folder: `Comics/{series}/{year}`
- File: `{series} v{volume} #{issue} ({year}).{ext}`

Movies
- Folder: `Movies/{title} ({year})`
- File: `{title} ({year}).{ext}`

---

## Caching strategy

### Provider cache
All provider results are cached in SQLite using:
- provider name
- normalized query string

### LLM cache
LLM results are cached using:
- file hash
- prompt version
- function name

---

## Testing

### Unit tests
- Template formatting and normalization
- Collision detection
- Cache key correctness

### Integration tests
- Scan a fixture directory into a temporary directory
- Approve a subset
- Generate plan
- Apply plan
- Rollback plan
- Verify paths and hashes

---

## Roadmap ideas
- Better video metadata extraction
- More robust audiobook series parsing
- Comic provider integration
- Sidecar metadata export for all types
- Pluggable provider system
- Duplicate resolution UI with quality heuristics

---

## Screenshots
Add screenshots here after running the UI:
- Dashboard
- Review Queue
- Plan Diff
- Settings