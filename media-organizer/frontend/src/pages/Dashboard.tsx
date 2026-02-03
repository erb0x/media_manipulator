import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getStats, getHealth } from '../api';
import type { StatsResponse, HealthResponse } from '../api';

export default function Dashboard() {
    const [stats, setStats] = useState<StatsResponse | null>(null);
    const [health, setHealth] = useState<HealthResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadData() {
            try {
                setLoading(true);
                const [statsData, healthData] = await Promise.all([
                    getStats(),
                    getHealth(),
                ]);
                setStats(statsData);
                setHealth(healthData);
                setError(null);
            } catch (err) {
                setError(err instanceof Error ? err.message : 'Failed to load data');
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, []);

    if (loading) {
        return (
            <div className="loading-overlay">
                <div className="spinner" />
                <span>Loading dashboard...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="empty-state">
                <div className="empty-state-title">Connection Error</div>
                <div className="empty-state-text">{error}</div>
                <Link to="/scan" className="btn btn-primary">
                    Start a New Scan
                </Link>
            </div>
        );
    }

    const formatDuration = (hours: number) => {
        if (hours < 1) return `${Math.round(hours * 60)} min`;
        return `${Math.round(hours)} hours`;
    };

    return (
        <div>
            <header className="page-header">
                <h1 className="page-title">Dashboard</h1>
                <p className="page-subtitle">
                    Overview of your media organization
                    {health && (
                        <span style={{ marginLeft: 'var(--space-md)' }}>
                            <span className="badge badge-approved">
                                Backend {health.status}
                            </span>
                        </span>
                    )}
                </p>
            </header>

            {/* Stats Grid */}
            <div className="card-grid" style={{ marginBottom: 'var(--space-xl)' }}>
                <div className="stat-card">
                    <div className="stat-card-value">{stats?.total_files || 0}</div>
                    <div className="stat-card-label">Total Files</div>
                </div>

                <div className="stat-card">
                    <div className="stat-card-value">{stats?.total_groups || 0}</div>
                    <div className="stat-card-label">Audiobook Groups</div>
                </div>

                <div className="stat-card">
                    <div className="stat-card-value">
                        {stats?.total_duration_hours ? formatDuration(stats.total_duration_hours) : '0'}
                    </div>
                    <div className="stat-card-label">Total Duration</div>
                </div>

                <div className="stat-card">
                    <div className="stat-card-value" style={{ color: 'var(--color-status-pending)' }}>
                        {stats?.pending_count || 0}
                    </div>
                    <div className="stat-card-label">Pending Review</div>
                </div>
            </div>

            {/* Status Breakdown */}
            <div className="card" style={{ marginBottom: 'var(--space-xl)' }}>
                <div className="card-header">
                    <h2 className="card-title">Processing Status</h2>
                </div>

                <div style={{ display: 'flex', gap: 'var(--space-lg)', flexWrap: 'wrap' }}>
                    <StatusItem
                        label="Pending"
                        count={stats?.pending_count || 0}
                        total={stats?.total_files || 0}
                        color="var(--color-status-pending)"
                    />
                    <StatusItem
                        label="Reviewed"
                        count={stats?.reviewed_count || 0}
                        total={stats?.total_files || 0}
                        color="var(--color-status-reviewed)"
                    />
                    <StatusItem
                        label="Approved"
                        count={stats?.approved_count || 0}
                        total={stats?.total_files || 0}
                        color="var(--color-status-approved)"
                    />
                    <StatusItem
                        label="Applied"
                        count={stats?.applied_count || 0}
                        total={stats?.total_files || 0}
                        color="var(--color-status-applied)"
                    />
                </div>
            </div>

            {/* Quick Actions */}
            <div className="card">
                <div className="card-header">
                    <h2 className="card-title">Quick Actions</h2>
                </div>

                <div style={{ display: 'flex', gap: 'var(--space-md)', flexWrap: 'wrap' }}>
                    <Link to="/scan" className="btn btn-primary btn-lg">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z" />
                        </svg>
                        Scan Folders
                    </Link>

                    {(stats?.pending_count || 0) > 0 && (
                        <Link to="/review" className="btn btn-secondary btn-lg">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z" />
                            </svg>
                            Review {stats?.pending_count} Pending
                        </Link>
                    )}

                    {(stats?.approved_count || 0) > 0 && (
                        <Link to="/plans" className="btn btn-success btn-lg">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                            </svg>
                            Generate Plan
                        </Link>
                    )}
                </div>
            </div>
        </div>
    );
}

function StatusItem({ label, count, total, color }: {
    label: string;
    count: number;
    total: number;
    color: string;
}) {
    const percentage = total > 0 ? (count / total) * 100 : 0;

    return (
        <div style={{ flex: 1, minWidth: '150px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-xs)' }}>
                <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
                    {label}
                </span>
                <span style={{ color, fontWeight: 'var(--font-weight-semibold)' }}>
                    {count}
                </span>
            </div>
            <div className="progress-bar">
                <div
                    className="progress-bar-fill"
                    style={{ width: `${percentage}%`, background: color }}
                />
            </div>
        </div>
    );
}
