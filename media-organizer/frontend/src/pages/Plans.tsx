import { useState, useEffect } from 'react';
import {
    listPlans,
    createPlan,
    getPlan,
    applyPlan,
    rollbackPlan,
    deletePlan,
} from '../api';
import type { Plan, PlannedOperation } from '../api';

export default function Plans() {
    const [plans, setPlans] = useState<Plan[]>([]);
    const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadPlans();
    }, []);

    async function loadPlans() {
        try {
            setLoading(true);
            const response = await listPlans();
            setPlans(response.items);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load plans');
        } finally {
            setLoading(false);
        }
    }

    async function handleCreatePlan() {
        try {
            setGenerating(true);
            setError(null);
            const plan = await createPlan({
                name: `Plan ${new Date().toLocaleDateString()}`,
                include_all_approved: true,
            });
            setPlans([plan, ...plans]);
            setSelectedPlan(plan);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to create plan');
        } finally {
            setGenerating(false);
        }
    }

    async function handleViewPlan(planId: string) {
        try {
            const plan = await getPlan(planId);
            setSelectedPlan(plan);
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to load plan');
        }
    }

    async function handleApplyPlan(planId: string) {
        if (!confirm('Are you sure you want to apply this plan? Files will be moved/renamed.')) {
            return;
        }

        try {
            await applyPlan(planId);
            alert('Plan is being applied. Check back for status updates.');
            loadPlans();
            if (selectedPlan?.id === planId) {
                handleViewPlan(planId);
            }
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to apply plan');
        }
    }

    async function handleRollbackPlan(planId: string) {
        if (!confirm('Are you sure you want to rollback this plan? Files will be restored to their original locations.')) {
            return;
        }

        try {
            const result = await rollbackPlan(planId);
            alert(`Rollback complete: ${result.operations_rolled_back} operations reversed.`);
            loadPlans();
            if (selectedPlan?.id === planId) {
                handleViewPlan(planId);
            }
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to rollback plan');
        }
    }

    async function handleDeletePlan(planId: string) {
        if (!confirm('Are you sure you want to delete this plan?')) {
            return;
        }

        try {
            await deletePlan(planId);
            setPlans(plans.filter(p => p.id !== planId));
            if (selectedPlan?.id === planId) {
                setSelectedPlan(null);
            }
        } catch (err) {
            alert(err instanceof Error ? err.message : 'Failed to delete plan');
        }
    }

    if (loading) {
        return (
            <div className="loading-overlay">
                <div className="spinner" />
                <span>Loading plans...</span>
            </div>
        );
    }

    return (
        <div>
            <header className="page-header">
                <h1 className="page-title">Organization Plans</h1>
                <p className="page-subtitle">
                    Generate and apply plans to organize your media files
                </p>
            </header>

            {error && (
                <div className="card" style={{ marginBottom: 'var(--space-lg)', background: 'rgba(244, 67, 54, 0.1)', borderColor: 'var(--color-error)' }}>
                    <div style={{ color: 'var(--color-error)' }}>{error}</div>
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xl)' }}>
                {/* Plan List */}
                <div>
                    <div className="card">
                        <div className="card-header">
                            <h2 className="card-title">Plans</h2>
                            <button
                                className="btn btn-primary"
                                onClick={handleCreatePlan}
                                disabled={generating}
                            >
                                {generating ? (
                                    <>
                                        <div className="spinner" style={{ width: 16, height: 16 }} />
                                        Generating...
                                    </>
                                ) : (
                                    <>
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
                                        </svg>
                                        New Plan
                                    </>
                                )}
                            </button>
                        </div>

                        {plans.length === 0 ? (
                            <div className="empty-state">
                                <div className="empty-state-title">No plans yet</div>
                                <div className="empty-state-text">
                                    Approve files in the Review Queue, then generate a plan to organize them.
                                </div>
                            </div>
                        ) : (
                            <div>
                                {plans.map(plan => (
                                    <div
                                        key={plan.id}
                                        className="file-row"
                                        onClick={() => handleViewPlan(plan.id)}
                                        style={{
                                            cursor: 'pointer',
                                            background: selectedPlan?.id === plan.id ? 'var(--color-surface-active)' : undefined,
                                        }}
                                    >
                                        <div className="file-icon">
                                            <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                                                <path d="M19 3h-4.18C14.4 1.84 13.3 1 12 1c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1z" />
                                            </svg>
                                        </div>

                                        <div className="file-info">
                                            <div className="file-title">{plan.name || 'Unnamed Plan'}</div>
                                            <div className="file-meta">
                                                {plan.item_count} operations
                                                {plan.completed_count > 0 && ` • ${plan.completed_count} completed`}
                                            </div>
                                        </div>

                                        <span className={`badge badge-${getStatusBadge(plan.status)}`}>
                                            {plan.status}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Plan Details */}
                <div>
                    {selectedPlan ? (
                        <div className="card">
                            <div className="card-header">
                                <h2 className="card-title">{selectedPlan.name || 'Plan Details'}</h2>
                                <span className={`badge badge-${getStatusBadge(selectedPlan.status)}`}>
                                    {selectedPlan.status}
                                </span>
                            </div>

                            {/* Actions */}
                            <div style={{ display: 'flex', gap: 'var(--space-sm)', marginBottom: 'var(--space-lg)' }}>
                                {selectedPlan.status === 'ready' && (
                                    <>
                                        <button
                                            className="btn btn-success"
                                            onClick={() => handleApplyPlan(selectedPlan.id)}
                                        >
                                            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                                <path d="M8 5v14l11-7z" />
                                            </svg>
                                            Apply Plan
                                        </button>
                                        <button
                                            className="btn btn-danger"
                                            onClick={() => handleDeletePlan(selectedPlan.id)}
                                        >
                                            Delete
                                        </button>
                                    </>
                                )}

                                {(selectedPlan.status === 'completed' || selectedPlan.status === 'failed') && (
                                    <button
                                        className="btn btn-warning"
                                        onClick={() => handleRollbackPlan(selectedPlan.id)}
                                    >
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                                            <path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z" />
                                        </svg>
                                        Rollback
                                    </button>
                                )}
                            </div>

                            {/* Stats */}
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--space-md)', marginBottom: 'var(--space-lg)' }}>
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-accent)' }}>
                                        {selectedPlan.item_count}
                                    </div>
                                    <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                                        Total
                                    </div>
                                </div>
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-success)' }}>
                                        {selectedPlan.completed_count}
                                    </div>
                                    <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                                        Completed
                                    </div>
                                </div>
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: 'var(--font-size-2xl)', fontWeight: 'var(--font-weight-bold)', color: 'var(--color-error)' }}>
                                        {selectedPlan.item_count - selectedPlan.completed_count}
                                    </div>
                                    <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                                        Remaining
                                    </div>
                                </div>
                            </div>

                            {/* Operations List */}
                            <h3 style={{ marginBottom: 'var(--space-md)', fontSize: 'var(--font-size-md)' }}>
                                Operations ({selectedPlan.operations?.length || 0})
                            </h3>

                            <div style={{ maxHeight: 400, overflowY: 'auto' }}>
                                {(selectedPlan.operations || []).slice(0, 50).map((op: PlannedOperation) => (
                                    <div
                                        key={op.id}
                                        style={{
                                            padding: 'var(--space-sm)',
                                            marginBottom: 'var(--space-xs)',
                                            background: 'var(--color-bg-tertiary)',
                                            borderRadius: 'var(--radius-sm)',
                                            fontSize: 'var(--font-size-sm)',
                                        }}
                                    >
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 'var(--space-xs)' }}>
                                            <span style={{
                                                textTransform: 'uppercase',
                                                fontSize: 'var(--font-size-xs)',
                                                color: 'var(--color-accent-muted)'
                                            }}>
                                                {op.operation_type}
                                            </span>
                                            <span className={`badge badge-${op.status === 'completed' ? 'approved' : op.status === 'failed' ? 'failed' : 'pending'}`}>
                                                {op.status}
                                            </span>
                                        </div>
                                        <div style={{ color: 'var(--color-text-muted)', wordBreak: 'break-all', marginBottom: 'var(--space-xs)' }}>
                                            From: {op.source_path}
                                        </div>
                                        <div style={{ color: 'var(--color-text-primary)', wordBreak: 'break-all' }}>
                                            To: {op.target_path}
                                        </div>
                                        {op.error_message && (
                                            <div style={{ color: 'var(--color-error)', marginTop: 'var(--space-xs)' }}>
                                                Error: {op.error_message}
                                            </div>
                                        )}
                                    </div>
                                ))}
                                {(selectedPlan.operations?.length || 0) > 50 && (
                                    <div style={{ textAlign: 'center', color: 'var(--color-text-muted)', padding: 'var(--space-md)' }}>
                                        +{selectedPlan.operations!.length - 50} more operations
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        <div className="card">
                            <div className="empty-state">
                                <div className="empty-state-title">Select a Plan</div>
                                <div className="empty-state-text">
                                    Click on a plan to view its details and operations
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

function getStatusBadge(status: string): string {
    switch (status) {
        case 'ready': return 'pending';
        case 'applying': return 'reviewed';
        case 'completed': return 'approved';
        case 'failed': return 'failed';
        case 'rolled_back': return 'pending';
        default: return 'pending';
    }
}
