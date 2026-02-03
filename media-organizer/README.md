# Media Organizer

Media Organizer is a modern, AI-powered desktop application designed to organize your audiobook library. It scans your chaotic media folders, intelligently identifies content using Google Gemini, and proposes a clean, organized structure for you to approve.

## ✨ Features

- **Smart Scanning**: Recursively scans directories to discover audiobooks, handling both multi-file folders and standalone M4B files.
- **AI-Powered Recognition**: Uses **Google Gemini Flash** to parse messy filenames and extract accurate metadata (Title, Author, Series, Narrator, Year).
- **Metadata Enrichment**: Fetches high-quality metadata from providers like Audnexus and Google Books.
- **Review Workflow**: Nothing happens without your say-so. Review AI suggestions in a dedicated queue before applying changes.
- **Safe Operations**: Generates a "Plan" of file moves and renames. Review the plan, then execute it with a single click.
- **Modern UI**: Built with React 19 and Tauri 2.0 for a native, high-performance experience.

## 🛠️ Tech Stack

### Frontend
- **Framework**: React 19 + TypeScript
- **Build Tool**: Vite
- **Desktop Runtime**: Tauri 2.0 (Rust)
- **Routing**: React Router 7
- **Styling**: CSS Variables + Custom Design System

### Backend
- **Server**: Python FastAPI (running as a local sidecar)
- **Database**: SQLite (via `aiosqlite`)
- **AI**: Google Generative AI (Gemini 1.5 Flash)
- **Audio Processing**: `mutagen` for metadata extraction
- **Packaging**: PyInstaller (compiles Python backend to a standalone binary)

## 🚀 Getting Started

### Prerequisites
- Node.js (v18+)
- Rust (latest stable)
- Python 3.9+
- A Google Gemini API Key (free tier available)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd media-organizer
   ```

2. **Setup Backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   ```

3. **Setup Frontend**
   ```bash
   cd ../frontend
   npm install
   ```

### Running Locally

You need two terminals to run the app in development mode:

**Terminal 1 (Backend Dev Server - optional if using Tauri dev):**
The Tauri dev command will automatically manage the backend, but you can run it standalone for API testing:
```bash
cd backend
python run_server.py
```

**Terminal 2 (Tauri App):**
```bash
cd frontend
npm run tauri:dev
```
*Note: You will need to configure your Gemini API Key in the application settings after launching.*

## 🏗️ Architecture

The application uses the **Tauri Sidecar** pattern:

1. **Tauri (Rust)**: Manages the native window, system tray, and lifecycle.
2. **Frontend (React)**: The user interface. It communicates with the Python backend via HTTP requests (allowed by Tauri's CSP).
3. **Backend (Python)**: A standalone executable spawned by Tauri. It handles:
   - File system access (scanning, moving, renaming)
   - Database operations (SQLite)
   - Heavy lifting (AI processing, metadata matching)

## ✅ Testing & Dry Runs

**Backend tests (pytest):**
```bash
cd backend
python -m pip install -e ".[dev]"
python -m pytest -q
```

**Backend tests (unittest fallback, no pytest needed):**
```bash
cd backend
python -m unittest discover -s tests_unittest -v
```

**Scanner dry-run (no DB writes, no file moves):**
```bash
cd backend
python scripts/scan_dry_run.py "C:\Users\mendj\Books\Audiobooks" --verify-duration --min-duration 1800
```

## 📦 Building for Production

To build the final application installer:

1. **Build the Python Backend**:
   ```bash
   cd backend
   pyinstaller media-organizer-backend.spec
   ```
   This creates the binary in `frontend/src-tauri/binaries/`.

2. **Build the Tauri App**:
   ```bash
   cd frontend
   npm run tauri:build
   ```
   The installer will be in `frontend/src-tauri/target/release/bundle/`.

## 🤝 Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
