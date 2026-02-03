import { useState, useEffect } from 'react';
import { startScan, listScans, deleteScan, getScanStatus } from '../api';
import type { ScanResponse, ScanStatusResponse } from '../api';

export default function ScanSetup() {
    const [rootPath, setRootPath] = useState('');
    const [scanName, setScanName] = useState('');
    const [exclusions, setExclusions] = useState('');
    const [scans, setScans] = useState<ScanResponse[]>([]);
    const [activeScan, setActiveScan] = useState<ScanStatusResponse | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadScans();
    }, []);

    // Poll for active scan status
    useEffect(() => {
        if (!activeScan || activeScan.status === 'completed' || activeScan.status === 'failed') {
            return;
        }

        const interval = setInterval(async () => {
            try {
                const status = await getScanStatus(activeScan.id);
                setActiveScan(status);

                if (status.status === 'completed' || status.status === 'failed') {
                    loadScans();
                }
            } catch (err) {
                console.error('Failed to get scan status:', err);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [activeScan]);

    async function loadScans() {
        try {
            const response = await listScans();
            setScans(response.items);
        } catch (err) {
            console.error('Failed to load scans:', err);
        }
    }

    async function handleStartScan(e: React.FormEvent) {
        e.preventDefault();

        if (!rootPath.trim()) {
            setError('Please enter a folder path');
            return;
        }

        try {
            setLoading(true);
            setError(null);

            const scan = await startScan({
                root_path: rootPath.trim(),
                name: scanName.trim() || undefined,
                exclusion_patterns: exclusions
                    .split('\n')
                    .map(p => p.trim())
                    .filter(p => p.length > 0),
            });

            setActiveScan({
                id: scan.id,
                status: scan.status,
                progress: 0,
                files_found: 0,
                files_processed: 0,
                current_file: null,
                error_message: null,
            });

            // Clear form
            setRootPath('');
            setScanName('');
            setExclusions('');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to start scan');
        } finally {
            setLoading(false);
        }
    }

    async function handleDeleteScan(scanId: string) {
        if (!confirm('Are you sure you want to delete this scan?')) {
            return;
        }

        try {
            await deleteScan(scanId);
            setScans(scans.filter(s => s.id !== scanId));
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to delete scan');
        }
    }

    return (
        <div>
            <header className="page-header">
                <h1 className="page-title">Scan Folders</h1>
                <p className="page-subtitle">
                    Scan folders for audiobooks and media files
                </p>
            </header>

            {/* Active Scan Progress */}
            {activeScan && activeScan.status === 'running' && (
                <div className="card" style={{ marginBottom: 'var(--space-xl)' }}>
                    <div className="card-header">
                        <h2 className="card-title">Scanning in Progress</h2>
                        <span className="badge badge-pending">Running</span>
                    </div>

                    <div style={{ marginBottom: 'var(--space-md)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-xs)' }}>
                            <span style={{ color: 'var(--color-text-secondary)' }}>
                                Progress: {activeScan.files_processed} / {activeScan.files_found} files
                            </span>
                            <span style={{ color: 'var(--color-accent)' }}>
                                {Math.round(activeScan.progress)}%
                            </span>
                        </div>
                        <div className="progress-bar">
                            <div
                                className="progress-bar-fill"
                                style={{ width: `${activeScan.progress}%` }}
                            />
                        </div>
                    </div>

                    {activeScan.current_file && (
                        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                            Currently processing: {activeScan.current_file}
                        </div>
                    )}
                </div>
            )}

            {/* New Scan Form */}
            <div className="card" style={{ marginBottom: 'var(--space-xl)' }}>
                <div className="card-header">
                    <h2 className="card-title">New Scan</h2>
                </div>

                <form onSubmit={handleStartScan}>
                    <div className="input-group">
                        <label className="input-label">Folder Path *</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="C:\Users\YourName\Audiobooks"
                            value={rootPath}
                            onChange={(e) => setRootPath(e.target.value)}
                            disabled={loading}
                        />
                    </div>

                    <div className="input-group">
                        <label className="input-label">Scan Name (optional)</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="My Audiobook Collection"
                            value={scanName}
                            onChange={(e) => setScanName(e.target.value)}
                            disabled={loading}
                        />
                    </div>

                    <div className="input-group">
                        <label className="input-label">Exclusion Patterns (one per line)</label>
                        <textarea
                            className="input"
                            placeholder="@eaDir
*.tmp
Thumbs.db"
                            rows={3}
                            value={exclusions}
                            onChange={(e) => setExclusions(e.target.value)}
                            disabled={loading}
                            style={{ resize: 'vertical' }}
                        />
                    </div>

                    {error && (
                        <div style={{
                            color: 'var(--color-error)',
                            marginBottom: 'var(--space-md)',
                            fontSize: 'var(--font-size-sm)'
                        }}>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="btn btn-primary btn-lg"
                        disabled={loading || (activeScan?.status === 'running')}
                    >
                        {loading ? (
                            <>
                                <div className="spinner" style={{ width: 16, height: 16 }} />
                                Starting...
                            </>
                        ) : (
                            <>
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z" />
                                </svg>
                                Start Scan
                            </>
                        )}
                    </button>
                </form>
            </div>

            {/* Previous Scans */}
            <div className="card">
                <div className="card-header">
                    <h2 className="card-title">Previous Scans</h2>
                </div>

                {scans.length === 0 ? (
                    <div className="empty-state">
                        <div className="empty-state-title">No scans yet</div>
                        <div className="empty-state-text">
                            Start a new scan to find audiobooks and media files
                        </div>
                    </div>
                ) : (
                    <div className="table-container">
                        <table className="table">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Path</th>
                                    <th>Status</th>
                                    <th>Files</th>
                                    <th>Groups</th>
                                    <th>Date</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody>
                                {scans.map(scan => (
                                    <tr key={scan.id}>
                                        <td>{scan.name || 'Unnamed Scan'}</td>
                                        <td style={{ maxWidth: 200 }} className="truncate">
                                            {scan.root_path}
                                        </td>
                                        <td>
                                            <span className={`badge badge-${scan.status === 'completed' ? 'approved' : scan.status === 'failed' ? 'failed' : 'pending'}`}>
                                                {scan.status}
                                            </span>
                                        </td>
                                        <td>{scan.files_found}</td>
                                        <td>{scan.groups_created}</td>
                                        <td>
                                            {scan.completed_at
                                                ? new Date(scan.completed_at).toLocaleDateString()
                                                : scan.started_at
                                                    ? new Date(scan.started_at).toLocaleDateString()
                                                    : '-'}
                                        </td>
                                        <td>
                                            <button
                                                className="btn btn-ghost btn-sm"
                                                onClick={() => handleDeleteScan(scan.id)}
                                                title="Delete scan"
                                            >
                                                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                                    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
                                                </svg>
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
