import { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
    getFile,
    updateFile,
    approveFile,
    searchProviders,
    applySearchResult,
} from '../api';
import type { MediaFile, ProviderSearchResult } from '../api';

export default function FileDetail() {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const [file, setFile] = useState<MediaFile | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Edit form state
    const [editForm, setEditForm] = useState({
        title: '',
        author: '',
        narrator: '',
        series: '',
        series_index: '',
        year: '',
    });

    // Search state
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<ProviderSearchResult[]>([]);
    const [searching, setSearching] = useState(false);
    const [showSearch, setShowSearch] = useState(false);

    useEffect(() => {
        if (id) loadFile();
    }, [id]);

    async function loadFile() {
        try {
            setLoading(true);
            const data = await getFile(id!);
            setFile(data);

            // Initialize form with file data
            setEditForm({
                title: data.final_title || data.extracted_title || '',
                author: data.final_author || data.extracted_author || '',
                narrator: data.final_narrator || data.extracted_narrator || '',
                series: data.final_series || data.extracted_series || '',
                series_index: String(data.final_series_index ?? data.extracted_series_index ?? ''),
                year: String(data.final_year ?? data.extracted_year ?? ''),
            });

            // Set initial search query
            setSearchQuery(`${data.extracted_title || ''} ${data.extracted_author || ''}`.trim());
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load file');
        } finally {
            setLoading(false);
        }
    }

    async function handleSave() {
        if (!file) return;

        try {
            setSaving(true);
            const updated = await updateFile(file.id, {
                final_title: editForm.title || null,
                final_author: editForm.author || null,
                final_narrator: editForm.narrator || null,
                final_series: editForm.series || null,
                final_series_index: editForm.series_index ? Number(editForm.series_index) : null,
                final_year: editForm.year ? Number(editForm.year) : null,
            });
            setFile(updated);
            alert('Changes saved!');
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to save');
        } finally {
            setSaving(false);
        }
    }

    async function handleApprove() {
        if (!file) return;

        try {
            setSaving(true);
            const updated = await approveFile(file.id);
            setFile(updated);
            navigate('/review');
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to approve');
        } finally {
            setSaving(false);
        }
    }

    async function handleSearch() {
        if (!searchQuery.trim()) return;

        try {
            setSearching(true);
            const response = await searchProviders({ query: searchQuery });
            setSearchResults(response.results);
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Search failed');
        } finally {
            setSearching(false);
        }
    }

    async function handleApplySearchResult(result: ProviderSearchResult) {
        if (!file) return;

        try {
            await applySearchResult(file.id, result);

            // Update form with result data
            setEditForm({
                title: result.title || editForm.title,
                author: result.author || editForm.author,
                narrator: result.narrator || editForm.narrator,
                series: result.series || editForm.series,
                series_index: result.series_index ? String(result.series_index) : editForm.series_index,
                year: result.year ? String(result.year) : editForm.year,
            });

            setShowSearch(false);
            loadFile();
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to apply result');
        }
    }

    if (loading) {
        return (
            <div className="loading-overlay">
                <div className="spinner" />
                <span>Loading file details...</span>
            </div>
        );
    }

    if (error || !file) {
        return (
            <div className="empty-state">
                <div className="empty-state-title">Error</div>
                <div className="empty-state-text">{error || 'File not found'}</div>
                <Link to="/review" className="btn btn-primary">
                    Back to Review Queue
                </Link>
            </div>
        );
    }

    const formatDuration = (seconds: number | null) => {
        if (!seconds) return '-';
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
    };

    const formatSize = (bytes: number) => {
        const mb = bytes / (1024 * 1024);
        return mb > 1000 ? `${(mb / 1024).toFixed(1)} GB` : `${mb.toFixed(1)} MB`;
    };

    return (
        <div>
            <header className="page-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
                    <Link to="/review" className="btn btn-ghost">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z" />
                        </svg>
                    </Link>
                    <div>
                        <h1 className="page-title">{editForm.title || file.file_name}</h1>
                        <p className="page-subtitle">
                            <span className={`badge badge-${file.status}`}>{file.status}</span>
                            {' • '}{formatDuration(file.duration_seconds)}
                            {' • '}{formatSize(file.file_size)}
                        </p>
                    </div>
                </div>
            </header>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: 'var(--space-xl)' }}>
                {/* Main Edit Form */}
                <div className="card">
                    <div className="card-header">
                        <h2 className="card-title">Metadata</h2>
                        <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => setShowSearch(!showSearch)}
                        >
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" />
                            </svg>
                            Search Providers
                        </button>
                    </div>

                    <div className="input-group">
                        <label className="input-label">Title</label>
                        <input
                            type="text"
                            className="input"
                            value={editForm.title}
                            onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
                        />
                    </div>

                    <div className="input-group">
                        <label className="input-label">Author</label>
                        <input
                            type="text"
                            className="input"
                            value={editForm.author}
                            onChange={(e) => setEditForm({ ...editForm, author: e.target.value })}
                        />
                    </div>

                    <div className="input-group">
                        <label className="input-label">Narrator</label>
                        <input
                            type="text"
                            className="input"
                            value={editForm.narrator}
                            onChange={(e) => setEditForm({ ...editForm, narrator: e.target.value })}
                        />
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px', gap: 'var(--space-md)' }}>
                        <div className="input-group">
                            <label className="input-label">Series</label>
                            <input
                                type="text"
                                className="input"
                                value={editForm.series}
                                onChange={(e) => setEditForm({ ...editForm, series: e.target.value })}
                            />
                        </div>
                        <div className="input-group">
                            <label className="input-label">Book #</label>
                            <input
                                type="number"
                                className="input"
                                value={editForm.series_index}
                                onChange={(e) => setEditForm({ ...editForm, series_index: e.target.value })}
                            />
                        </div>
                    </div>

                    <div className="input-group">
                        <label className="input-label">Year</label>
                        <input
                            type="number"
                            className="input"
                            style={{ width: 120 }}
                            value={editForm.year}
                            onChange={(e) => setEditForm({ ...editForm, year: e.target.value })}
                        />
                    </div>

                    <div style={{ display: 'flex', gap: 'var(--space-sm)', marginTop: 'var(--space-lg)' }}>
                        <button
                            className="btn btn-primary"
                            onClick={handleSave}
                            disabled={saving}
                        >
                            {saving ? 'Saving...' : 'Save Changes'}
                        </button>

                        {file.status !== 'approved' && file.status !== 'applied' && (
                            <button
                                className="btn btn-success"
                                onClick={handleApprove}
                                disabled={saving}
                            >
                                Save & Approve
                            </button>
                        )}
                    </div>
                </div>

                {/* Sidebar / Search Results */}
                <div>
                    {/* File Info */}
                    <div className="card" style={{ marginBottom: 'var(--space-lg)' }}>
                        <h3 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>File Info</h3>

                        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                            <div style={{ marginBottom: 'var(--space-sm)' }}>
                                <strong>Path:</strong>
                                <div style={{ wordBreak: 'break-all', marginTop: 'var(--space-xs)' }}>
                                    {file.file_path}
                                </div>
                            </div>

                            <div style={{ marginBottom: 'var(--space-sm)' }}>
                                <strong>Type:</strong> {file.media_type}
                            </div>

                            {file.confidence && (
                                <div style={{ marginBottom: 'var(--space-sm)' }}>
                                    <strong>Confidence:</strong> {Math.round(file.confidence * 100)}%
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Provider Search */}
                    {showSearch && (
                        <div className="card">
                            <h3 className="card-title" style={{ marginBottom: 'var(--space-md)' }}>
                                Search Providers
                            </h3>

                            <div style={{ display: 'flex', gap: 'var(--space-sm)', marginBottom: 'var(--space-md)' }}>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="Search..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                                />
                                <button
                                    className="btn btn-primary"
                                    onClick={handleSearch}
                                    disabled={searching}
                                >
                                    {searching ? '...' : 'Search'}
                                </button>
                            </div>

                            {searchResults.length === 0 ? (
                                <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-sm)' }}>
                                    No results yet. Enter a search query above.
                                </div>
                            ) : (
                                <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                                    {searchResults.map((result, i) => (
                                        <div
                                            key={i}
                                            style={{
                                                padding: 'var(--space-sm)',
                                                marginBottom: 'var(--space-sm)',
                                                background: 'var(--color-bg-tertiary)',
                                                borderRadius: 'var(--radius-md)',
                                                cursor: 'pointer',
                                            }}
                                            onClick={() => handleApplySearchResult(result)}
                                        >
                                            <div style={{ fontWeight: 'var(--font-weight-medium)', marginBottom: 'var(--space-xs)' }}>
                                                {result.title}
                                            </div>
                                            <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                                                {result.author}
                                                {result.narrator && ` • ${result.narrator}`}
                                                {result.year && ` • ${result.year}`}
                                            </div>
                                            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-xs)' }}>
                                                via {result.provider} ({Math.round(result.confidence * 100)}% match)
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
