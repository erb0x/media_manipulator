import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
    listFiles,
    listGroups,
    approveFile,
    approveGroup,
    bulkApprove,
} from '../api';
import type { MediaFile, AudiobookGroup } from '../api';

type ViewMode = 'files' | 'groups';
type StatusFilter = '' | 'pending' | 'reviewed' | 'approved';

export default function ReviewQueue() {
    const [viewMode, setViewMode] = useState<ViewMode>('files');
    const [statusFilter, setStatusFilter] = useState<StatusFilter>('');
    const [search, setSearch] = useState('');

    const [files, setFiles] = useState<MediaFile[]>([]);
    const [groups, setGroups] = useState<AudiobookGroup[]>([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalCount, setTotalCount] = useState(0);
    const [hasMore, setHasMore] = useState(false);

    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

    useEffect(() => {
        loadData();
    }, [viewMode, statusFilter, search, page]);

    async function loadData() {
        try {
            setLoading(true);

            if (viewMode === 'files') {
                const response = await listFiles({
                    page,
                    page_size: 20,
                    status: statusFilter || undefined,
                    search: search || undefined,
                });
                setFiles(response.items);
                setTotalCount(response.total);
                setHasMore(response.has_more);
            } else {
                const response = await listGroups({
                    page,
                    page_size: 20,
                    status: statusFilter || undefined,
                });
                setGroups(response.items);
                setTotalCount(response.total);
                setHasMore(response.has_more);
            }
        } catch (err) {
            console.error('Failed to load data:', err);
        } finally {
            setLoading(false);
        }
    }

    async function handleApprove(id: string, isGroup: boolean) {
        try {
            if (isGroup) {
                const updated = await approveGroup(id);
                setGroups(groups.map(g => g.id === id ? { ...g, status: updated.status } : g));
            } else {
                const updated = await approveFile(id);
                setFiles(files.map(f => f.id === id ? { ...f, status: updated.status } : f));
            }
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to approve');
        }
    }

    async function handleBulkApprove() {
        if (selectedIds.size === 0) return;

        try {
            const fileIds = viewMode === 'files' ? Array.from(selectedIds) : [];
            const groupIds = viewMode === 'groups' ? Array.from(selectedIds) : [];

            await bulkApprove(fileIds, groupIds);
            setSelectedIds(new Set());
            loadData();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to bulk approve');
        }
    }

    function toggleSelection(id: string) {
        const newSelected = new Set(selectedIds);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        setSelectedIds(newSelected);
    }

    function selectAll() {
        const items = viewMode === 'files' ? files : groups;
        if (selectedIds.size === items.length) {
            setSelectedIds(new Set());
        } else {
            setSelectedIds(new Set(items.map(i => i.id)));
        }
    }

    const formatDuration = (seconds: number | null) => {
        if (!seconds) return '-';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
    };

    return (
        <div>
            <header className="page-header">
                <h1 className="page-title">Review Queue</h1>
                <p className="page-subtitle">
                    Review and approve media files for organization
                </p>
            </header>

            {/* Toolbar */}
            <div className="card" style={{ marginBottom: 'var(--space-lg)', padding: 'var(--space-md)' }}>
                <div style={{ display: 'flex', gap: 'var(--space-md)', alignItems: 'center', flexWrap: 'wrap' }}>
                    {/* View Mode Toggle */}
                    <div style={{ display: 'flex', background: 'var(--color-bg-tertiary)', borderRadius: 'var(--radius-md)' }}>
                        <button
                            className={`btn btn-sm ${viewMode === 'files' ? 'btn-primary' : 'btn-ghost'}`}
                            onClick={() => { setViewMode('files'); setPage(1); setSelectedIds(new Set()); }}
                        >
                            Files
                        </button>
                        <button
                            className={`btn btn-sm ${viewMode === 'groups' ? 'btn-primary' : 'btn-ghost'}`}
                            onClick={() => { setViewMode('groups'); setPage(1); setSelectedIds(new Set()); }}
                        >
                            Groups
                        </button>
                    </div>

                    {/* Status Filter */}
                    <select
                        className="input"
                        style={{ width: 'auto' }}
                        value={statusFilter}
                        onChange={(e) => { setStatusFilter(e.target.value as StatusFilter); setPage(1); }}
                    >
                        <option value="">All Status</option>
                        <option value="pending">Pending</option>
                        <option value="reviewed">Reviewed</option>
                        <option value="approved">Approved</option>
                    </select>

                    {/* Search */}
                    {viewMode === 'files' && (
                        <input
                            type="text"
                            className="input"
                            placeholder="Search files..."
                            style={{ width: 200 }}
                            value={search}
                            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                        />
                    )}

                    <div style={{ flex: 1 }} />

                    {/* Bulk Actions */}
                    {selectedIds.size > 0 && (
                        <button className="btn btn-success" onClick={handleBulkApprove}>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                            </svg>
                            Approve {selectedIds.size} Selected
                        </button>
                    )}

                    <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                        {totalCount} total
                    </span>
                </div>
            </div>

            {/* Content */}
            {loading ? (
                <div className="loading-overlay">
                    <div className="spinner" />
                    <span>Loading...</span>
                </div>
            ) : viewMode === 'files' ? (
                <FileList
                    files={files}
                    selectedIds={selectedIds}
                    onToggleSelect={toggleSelection}
                    onSelectAll={selectAll}
                    onApprove={(id) => handleApprove(id, false)}
                    formatDuration={formatDuration}
                />
            ) : (
                <GroupList
                    groups={groups}
                    selectedIds={selectedIds}
                    onToggleSelect={toggleSelection}
                    onSelectAll={selectAll}
                    onApprove={(id) => handleApprove(id, true)}
                    formatDuration={formatDuration}
                />
            )}

            {/* Pagination */}
            {(hasMore || page > 1) && (
                <div style={{ display: 'flex', justifyContent: 'center', gap: 'var(--space-md)', marginTop: 'var(--space-lg)' }}>
                    <button
                        className="btn btn-secondary"
                        disabled={page === 1}
                        onClick={() => setPage(page - 1)}
                    >
                        Previous
                    </button>
                    <span style={{ display: 'flex', alignItems: 'center', color: 'var(--color-text-secondary)' }}>
                        Page {page}
                    </span>
                    <button
                        className="btn btn-secondary"
                        disabled={!hasMore}
                        onClick={() => setPage(page + 1)}
                    >
                        Next
                    </button>
                </div>
            )}
        </div>
    );
}

function FileList({ files, selectedIds, onToggleSelect, onSelectAll, onApprove, formatDuration }: {
    files: MediaFile[];
    selectedIds: Set<string>;
    onToggleSelect: (id: string) => void;
    onSelectAll: () => void;
    onApprove: (id: string) => void;
    formatDuration: (seconds: number | null) => string;
}) {
    if (files.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-state-title">No files found</div>
                <div className="empty-state-text">
                    Scan a folder to find media files
                </div>
            </div>
        );
    }

    return (
        <div>
            <div style={{ marginBottom: 'var(--space-sm)', display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                <input
                    type="checkbox"
                    checked={selectedIds.size === files.length && files.length > 0}
                    onChange={onSelectAll}
                />
                <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                    Select all
                </span>
            </div>

            {files.map(file => (
                <div key={file.id} className="file-row">
                    <input
                        type="checkbox"
                        checked={selectedIds.has(file.id)}
                        onChange={() => onToggleSelect(file.id)}
                    />

                    <div className="file-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z" />
                        </svg>
                    </div>

                    <div className="file-info">
                        <Link to={`/review/${file.id}`} className="file-title">
                            {file.final_title || file.extracted_title || file.file_name}
                        </Link>
                        <div className="file-meta">
                            {file.final_author || file.extracted_author || 'Unknown Author'}
                            {file.duration_seconds && ` • ${formatDuration(file.duration_seconds)}`}
                        </div>
                    </div>

                    <span className={`badge badge-${file.status}`}>
                        {file.status}
                    </span>

                    <div className="file-actions">
                        {file.status !== 'approved' && file.status !== 'applied' && (
                            <button
                                className="btn btn-success btn-sm"
                                onClick={() => onApprove(file.id)}
                            >
                                Approve
                            </button>
                        )}
                        <Link to={`/review/${file.id}`} className="btn btn-secondary btn-sm">
                            Edit
                        </Link>
                    </div>
                </div>
            ))}
        </div>
    );
}

function GroupList({ groups, selectedIds, onToggleSelect, onSelectAll, onApprove, formatDuration }: {
    groups: AudiobookGroup[];
    selectedIds: Set<string>;
    onToggleSelect: (id: string) => void;
    onSelectAll: () => void;
    onApprove: (id: string) => void;
    formatDuration: (seconds: number | null) => string;
}) {
    if (groups.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-state-title">No groups found</div>
                <div className="empty-state-text">
                    Audiobook groups are created when multiple files are found in the same folder
                </div>
            </div>
        );
    }

    return (
        <div>
            <div style={{ marginBottom: 'var(--space-sm)', display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
                <input
                    type="checkbox"
                    checked={selectedIds.size === groups.length && groups.length > 0}
                    onChange={onSelectAll}
                />
                <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                    Select all
                </span>
            </div>

            {groups.map(group => (
                <div key={group.id} className="file-row">
                    <input
                        type="checkbox"
                        checked={selectedIds.has(group.id)}
                        onChange={() => onToggleSelect(group.id)}
                    />

                    <div className="file-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-8 12.5v-9l6 4.5-6 4.5z" />
                        </svg>
                    </div>

                    <div className="file-info">
                        <div className="file-title">
                            {group.final_title || group.title}
                        </div>
                        <div className="file-meta">
                            {group.final_author || group.author || 'Unknown Author'}
                            {' • '}{group.file_count} files
                            {group.total_duration && ` • ${formatDuration(group.total_duration)}`}
                        </div>
                    </div>

                    <span className={`badge badge-${group.status}`}>
                        {group.status}
                    </span>

                    <div className="file-actions">
                        {group.status !== 'approved' && group.status !== 'applied' && (
                            <button
                                className="btn btn-success btn-sm"
                                onClick={() => onApprove(group.id)}
                            >
                                Approve
                            </button>
                        )}
                        <button className="btn btn-secondary btn-sm">
                            Edit
                        </button>
                    </div>
                </div>
            ))}
        </div>
    );
}
