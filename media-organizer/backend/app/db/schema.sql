-- Media Organizer Database Schema
-- SQLite DDL for audiobooks, ebooks, and comics organization

-- Application settings stored in database
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Scan jobs tracking
CREATE TABLE IF NOT EXISTS scans (
    id TEXT PRIMARY KEY,
    root_path TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, running, completed, failed
    started_at TEXT,
    completed_at TEXT,
    files_found INTEGER DEFAULT 0,
    groups_created INTEGER DEFAULT 0,
    error_message TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Individual media files
CREATE TABLE IF NOT EXISTS media_files (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    file_path TEXT NOT NULL UNIQUE,
    file_hash TEXT,  -- SHA-256
    file_size INTEGER,
    media_type TEXT NOT NULL,  -- audiobook, ebook, comic
    
    -- Grouping for multi-file audiobooks
    group_id TEXT,
    is_group_primary BOOLEAN DEFAULT FALSE,
    track_number INTEGER,  -- For ordering tracks in a group
    
    -- Extracted metadata (from file tags/embedded data)
    extracted_title TEXT,
    extracted_author TEXT,
    extracted_narrator TEXT,
    extracted_series TEXT,
    extracted_series_index REAL,
    extracted_year INTEGER,
    duration_seconds INTEGER,
    
    -- User-approved final metadata
    final_title TEXT,
    final_author TEXT,
    final_narrator TEXT,
    final_series TEXT,
    final_series_index REAL,
    final_year INTEGER,
    
    -- Workflow status
    status TEXT DEFAULT 'pending',  -- pending, reviewed, approved, applied
    confidence REAL DEFAULT 0.0,
    proposed_path TEXT,
    
    -- Provider match info
    provider_match_source TEXT,  -- google_books, audnexus, etc.
    provider_match_id TEXT,  -- ASIN, ISBN, etc.
    
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

-- Audiobook groups (for multi-file audiobooks)
CREATE TABLE IF NOT EXISTS audiobook_groups (
    id TEXT PRIMARY KEY,
    scan_id TEXT NOT NULL,
    folder_path TEXT NOT NULL UNIQUE,
    file_count INTEGER DEFAULT 0,
    total_duration_seconds INTEGER DEFAULT 0,
    
    -- Consolidated metadata from primary file or folder
    title TEXT,
    author TEXT,
    narrator TEXT,
    series TEXT,
    series_index REAL,
    year INTEGER,
    
    -- User-approved final metadata
    final_title TEXT,
    final_author TEXT,
    final_narrator TEXT,
    final_series TEXT,
    final_series_index REAL,
    final_year INTEGER,
    
    -- Workflow status
    status TEXT DEFAULT 'pending',  -- pending, reviewed, approved, applied
    confidence REAL DEFAULT 0.0,
    proposed_path TEXT,
    
    -- Provider match info
    provider_match_source TEXT,
    provider_match_id TEXT,
    
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    
    FOREIGN KEY (scan_id) REFERENCES scans(id) ON DELETE CASCADE
);

-- Provider API response cache
CREATE TABLE IF NOT EXISTS provider_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    query_key TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT,
    UNIQUE(provider, query_key)
);

-- LLM response cache
CREATE TABLE IF NOT EXISTS llm_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    function_name TEXT NOT NULL,
    response_json TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(file_hash, prompt_version, function_name)
);

-- Organization plans
CREATE TABLE IF NOT EXISTS plans (
    id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    status TEXT DEFAULT 'draft',  -- draft, ready, applying, completed, rolled_back, failed
    created_at TEXT DEFAULT (datetime('now')),
    applied_at TEXT,
    rolled_back_at TEXT,
    item_count INTEGER DEFAULT 0,
    completed_count INTEGER DEFAULT 0,
    error_message TEXT
);

-- Individual operations within a plan
CREATE TABLE IF NOT EXISTS planned_operations (
    id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    media_file_id TEXT,
    group_id TEXT,
    operation_type TEXT NOT NULL,  -- move, rename, copy_delete
    source_path TEXT NOT NULL,
    target_path TEXT NOT NULL,
    file_hash TEXT,  -- For verification before apply
    execution_order INTEGER,  -- Order to execute operations
    status TEXT DEFAULT 'pending',  -- pending, completed, failed, rolled_back, skipped
    executed_at TEXT,
    error_message TEXT,
    
    FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
);

-- Audit log for all file operations
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT,
    operation_id TEXT,
    action TEXT NOT NULL,  -- apply, rollback, skip, error
    source_path TEXT,
    target_path TEXT,
    file_hash TEXT,
    result TEXT,  -- success, failed, skipped
    error_message TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_media_files_status ON media_files(status);
CREATE INDEX IF NOT EXISTS idx_media_files_scan ON media_files(scan_id);
CREATE INDEX IF NOT EXISTS idx_media_files_group ON media_files(group_id);
CREATE INDEX IF NOT EXISTS idx_media_files_type ON media_files(media_type);
CREATE INDEX IF NOT EXISTS idx_media_files_path ON media_files(file_path);
CREATE INDEX IF NOT EXISTS idx_audiobook_groups_scan ON audiobook_groups(scan_id);
CREATE INDEX IF NOT EXISTS idx_audiobook_groups_status ON audiobook_groups(status);
CREATE INDEX IF NOT EXISTS idx_provider_cache_lookup ON provider_cache(provider, query_key);
CREATE INDEX IF NOT EXISTS idx_llm_cache_lookup ON llm_cache(file_hash, prompt_version, function_name);
CREATE INDEX IF NOT EXISTS idx_planned_operations_plan ON planned_operations(plan_id);
CREATE INDEX IF NOT EXISTS idx_planned_operations_status ON planned_operations(status);
CREATE INDEX IF NOT EXISTS idx_audit_log_plan ON audit_log(plan_id);
