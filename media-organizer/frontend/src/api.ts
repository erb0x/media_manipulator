/**
 * API client for the Media Organizer backend.
 * Handles all HTTP communication with the backend server.
 */

const API_BASE_URL = 'http://localhost:8742/api';

/**
 * Generic fetch wrapper with error handling
 */
async function fetchAPI<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;

    const response = await fetch(url, {
        headers: {
            'Content-Type': 'application/json',
            ...options.headers,
        },
        ...options,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
}

// ==================== Health ====================

export interface HealthResponse {
    status: string;
    version: string;
    database: string;
}

export async function getHealth(): Promise<HealthResponse> {
    return fetchAPI<HealthResponse>('http://localhost:8742/health');
}

// ==================== Settings ====================

export interface SettingsResponse {
    output_root: string | null;
    audiobook_folder_template: string;
    audiobook_file_template: string;
    enable_llm: boolean;
    enable_providers: boolean;
    gemini_key_loaded: boolean;
    google_books_key_loaded: boolean;
}

export interface SettingsUpdateRequest {
    output_root?: string;
    audiobook_folder_template?: string;
    audiobook_file_template?: string;
    enable_llm?: boolean;
    enable_providers?: boolean;
}

export async function getSettings(): Promise<SettingsResponse> {
    return fetchAPI<SettingsResponse>('/settings');
}

export async function updateSettings(data: SettingsUpdateRequest): Promise<SettingsResponse> {
    return fetchAPI<SettingsResponse>('/settings', {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

// ==================== Scans ====================

export interface ScanStartRequest {
    root_paths: string[];
    name?: string;
    exclusion_patterns?: string[];
}

export interface ScanResponse {
    id: string;
    name: string;
    root_path: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    files_found: number;
    files_processed: number;
    groups_created: number;
    started_at: string | null;
    completed_at: string | null;
    error_message: string | null;
}

export interface ScanStatusResponse {
    id: string;
    status: string;
    progress: number;
    files_found: number;
    files_processed: number;
    current_file: string | null;
    error_message: string | null;
}

export interface ScanListResponse {
    total: number;
    page: number;
    page_size: number;
    has_more: boolean;
    items: ScanResponse[];
}

export async function startScan(data: ScanStartRequest): Promise<ScanResponse> {
    return fetchAPI<ScanResponse>('/scan/start', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function getScanStatus(scanId: string): Promise<ScanStatusResponse> {
    return fetchAPI<ScanStatusResponse>(`/scan/status/${scanId}`);
}

export async function listScans(page = 1, pageSize = 20): Promise<ScanListResponse> {
    return fetchAPI<ScanListResponse>(`/scan?page=${page}&page_size=${pageSize}`);
}

export async function deleteScan(scanId: string): Promise<void> {
    await fetchAPI(`/scan/${scanId}`, { method: 'DELETE' });
}

// ==================== Files ====================

export interface MediaFile {
    id: string;
    file_path: string;
    file_name: string;
    media_type: string;
    status: 'pending' | 'reviewed' | 'approved' | 'applied' | 'failed';

    // Extracted metadata
    extracted_title: string | null;
    extracted_author: string | null;
    extracted_narrator: string | null;
    extracted_series: string | null;
    extracted_series_index: number | null;
    extracted_year: number | null;
    extracted_parent_series: string | null;

    // Final metadata (after user edits)
    final_title: string | null;
    final_author: string | null;
    final_narrator: string | null;
    final_series: string | null;
    final_series_index: number | null;
    final_year: number | null;
    final_parent_series: string | null;

    duration_seconds: number | null;
    file_size: number;
    confidence: number | null;

    created_at: string;
    updated_at: string;
}

export interface AudiobookGroup {
    id: string;
    title: string;
    author: string | null;
    narrator: string | null;
    series: string | null;
    series_index: number | null;
    year: number | null;
    status: 'pending' | 'reviewed' | 'approved' | 'applied' | 'failed';
    file_count: number;
    total_duration: number | null;

    // Final metadata
    final_title: string | null;
    final_author: string | null;
    final_narrator: string | null;
    final_series: string | null;
    final_series_index: number | null;
    final_year: number | null;
    final_parent_series: string | null;

    confidence: number | null;
    files?: MediaFile[];
}

export interface FileListResponse {
    total: number;
    page: number;
    page_size: number;
    has_more: boolean;
    items: MediaFile[];
}

export interface GroupListResponse {
    total: number;
    page: number;
    page_size: number;
    has_more: boolean;
    items: AudiobookGroup[];
}

export interface StatsResponse {
    total_files: number;
    total_groups: number;
    pending_count: number;
    reviewed_count: number;
    approved_count: number;
    applied_count: number;
    total_duration_hours: number;
}

export async function listFiles(params: {
    page?: number;
    page_size?: number;
    status?: string;
    media_type?: string;
    search?: string;
} = {}): Promise<FileListResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', String(params.page));
    if (params.page_size) searchParams.set('page_size', String(params.page_size));
    if (params.status) searchParams.set('status', params.status);
    if (params.media_type) searchParams.set('media_type', params.media_type);
    if (params.search) searchParams.set('search', params.search);

    return fetchAPI<FileListResponse>(`/files?${searchParams}`);
}

export async function getFile(fileId: string): Promise<MediaFile> {
    return fetchAPI<MediaFile>(`/files/${fileId}`);
}

export async function updateFile(fileId: string, data: Partial<MediaFile>): Promise<MediaFile> {
    return fetchAPI<MediaFile>(`/files/${fileId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function approveFile(fileId: string): Promise<MediaFile> {
    return fetchAPI<MediaFile>(`/files/${fileId}/approve`, { method: 'POST' });
}

export async function listGroups(params: {
    page?: number;
    page_size?: number;
    status?: string;
} = {}): Promise<GroupListResponse> {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.set('page', String(params.page));
    if (params.page_size) searchParams.set('page_size', params.page_size.toString());
    if (params.status) searchParams.set('status', params.status);

    return fetchAPI<GroupListResponse>(`/files/groups?${searchParams}`);
}

export async function getGroup(groupId: string): Promise<AudiobookGroup> {
    return fetchAPI<AudiobookGroup>(`/files/groups/${groupId}`);
}

export async function updateGroup(groupId: string, data: Partial<AudiobookGroup>): Promise<AudiobookGroup> {
    return fetchAPI<AudiobookGroup>(`/files/groups/${groupId}`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

export async function approveGroup(groupId: string): Promise<AudiobookGroup> {
    return fetchAPI<AudiobookGroup>(`/files/groups/${groupId}/approve`, { method: 'POST' });
}

export async function getStats(): Promise<StatsResponse> {
    return fetchAPI<StatsResponse>('/files/stats');
}

export async function enrichFile(fileId: string, force = false): Promise<MediaFile> {
    return fetchAPI<MediaFile>(`/files/${fileId}/enrich?force=${force}`, { method: 'POST' });
}

export async function enrichGroup(groupId: string, force = false): Promise<AudiobookGroup> {
    return fetchAPI<AudiobookGroup>(`/files/groups/${groupId}/enrich?force=${force}`, { method: 'POST' });
}

export interface BulkEnrichResponse {
    files: { id: string; success: boolean; error?: string }[];
    groups: { id: string; success: boolean; error?: string }[];
}

export async function bulkEnrich(fileIds: string[], groupIds: string[]): Promise<BulkEnrichResponse> {
    return fetchAPI<BulkEnrichResponse>('/files/bulk-enrich', {
        method: 'POST',
        body: JSON.stringify({ file_ids: fileIds, group_ids: groupIds }),
    });
}

export async function bulkApprove(fileIds: string[], groupIds: string[]): Promise<{ approved_files: number; approved_groups: number }> {
    return fetchAPI('/files/bulk-approve', {
        method: 'POST',
        body: JSON.stringify({ file_ids: fileIds, group_ids: groupIds }),
    });
}

// ==================== Plans ====================

export interface PlannedOperation {
    id: string;
    operation_type: 'move' | 'rename' | 'copy_delete';
    source_path: string;
    target_path: string;
    status: 'pending' | 'completed' | 'failed' | 'rolled_back';
    executed_at: string | null;
    error_message: string | null;
}

export interface Plan {
    id: string;
    name: string | null;
    description: string | null;
    status: 'ready' | 'applying' | 'completed' | 'failed' | 'rolled_back';
    created_at: string;
    applied_at: string | null;
    rolled_back_at: string | null;
    item_count: number;
    completed_count: number;
    error_message: string | null;
    operations: PlannedOperation[];
}

export interface PlanListResponse {
    total: number;
    page: number;
    page_size: number;
    has_more: boolean;
    items: Plan[];
}

export interface PlanCreateRequest {
    name?: string;
    description?: string;
    file_ids?: string[];
    group_ids?: string[];
    include_all_approved?: boolean;
}

export async function listPlans(page = 1, pageSize = 20): Promise<PlanListResponse> {
    return fetchAPI<PlanListResponse>(`/plans?page=${page}&page_size=${pageSize}`);
}

export async function createPlan(data: PlanCreateRequest): Promise<Plan> {
    return fetchAPI<Plan>('/plans/generate', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

export async function getPlan(planId: string): Promise<Plan> {
    return fetchAPI<Plan>(`/plans/${planId}`);
}

export async function applyPlan(planId: string): Promise<{ message: string; plan_id: string }> {
    return fetchAPI(`/plans/${planId}/apply`, { method: 'POST' });
}

export async function rollbackPlan(planId: string): Promise<{
    message: string;
    plan_id: string;
    operations_rolled_back: number;
    operations_failed: number;
}> {
    return fetchAPI(`/plans/${planId}/rollback`, { method: 'POST' });
}

export async function deletePlan(planId: string): Promise<void> {
    await fetchAPI(`/plans/${planId}`, { method: 'DELETE' });
}

// ==================== Search ====================

export interface ProviderSearchResult {
    provider: string;
    id: string;
    title: string;
    author: string | null;
    narrator: string | null;
    series: string | null;
    series_index: number | null;
    year: number | null;
    parent_series?: string | null;
    description: string | null;
    cover_url: string | null;
    confidence: number;
}

export interface ProviderSearchResponse {
    query: string;
    results: ProviderSearchResult[];
    cached: boolean;
}

export async function searchProviders(params: {
    query?: string;
    title?: string;
    author?: string;
    asin?: string;
    provider?: string;
}): Promise<ProviderSearchResponse> {
    const searchParams = new URLSearchParams();
    if (params.query) searchParams.set('query', params.query);
    if (params.title) searchParams.set('title', params.title);
    if (params.author) searchParams.set('author', params.author);
    if (params.asin) searchParams.set('asin', params.asin);
    if (params.provider) searchParams.set('provider', params.provider);

    return fetchAPI<ProviderSearchResponse>(`/search?${searchParams}`);
}

export async function applySearchResult(
    fileId: string,
    result: ProviderSearchResult
): Promise<{ message: string; file_id: string }> {
    return fetchAPI(`/search/apply/${fileId}`, {
        method: 'POST',
        body: JSON.stringify(result),
    });
}

export async function applySearchResultToGroup(
    groupId: string,
    result: ProviderSearchResult
): Promise<{ message: string; group_id: string }> {
    return fetchAPI(`/search/apply-group/${groupId}`, {
        method: 'POST',
        body: JSON.stringify(result),
    });
}
