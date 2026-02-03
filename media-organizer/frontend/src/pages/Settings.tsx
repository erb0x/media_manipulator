import { useState, useEffect } from 'react';
import { getSettings, updateSettings } from '../api';
import type { SettingsResponse } from '../api';

export default function Settings() {
    const [settings, setSettings] = useState<SettingsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Form state
    const [outputRoot, setOutputRoot] = useState('');
    const [folderTemplate, setFolderTemplate] = useState('');
    const [fileTemplate, setFileTemplate] = useState('');
    const [enableLLM, setEnableLLM] = useState(false);
    const [enableProviders, setEnableProviders] = useState(false);

    useEffect(() => {
        loadSettings();
    }, []);

    async function loadSettings() {
        try {
            setLoading(true);
            const data = await getSettings();
            setSettings(data);

            // Initialize form
            setOutputRoot(data.output_root || '');
            setFolderTemplate(data.audiobook_folder_template || '');
            setFileTemplate(data.audiobook_file_template || '');
            setEnableLLM(data.enable_llm);
            setEnableProviders(data.enable_providers);
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to load settings');
        } finally {
            setLoading(false);
        }
    }

    async function handleSave() {
        try {
            setSaving(true);
            setError(null);

            const updated = await updateSettings({
                output_root: outputRoot || undefined,
                audiobook_folder_template: folderTemplate || undefined,
                audiobook_file_template: fileTemplate || undefined,
                enable_llm: enableLLM,
                enable_providers: enableProviders,
            });

            setSettings(updated);
            alert('Settings saved successfully!');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to save settings');
        } finally {
            setSaving(false);
        }
    }

    if (loading) {
        return (
            <div className="loading-overlay">
                <div className="spinner" />
                <span>Loading settings...</span>
            </div>
        );
    }

    return (
        <div>
            <header className="page-header">
                <h1 className="page-title">Settings</h1>
                <p className="page-subtitle">
                    Configure application settings and preferences
                </p>
            </header>

            {error && (
                <div className="card" style={{ marginBottom: 'var(--space-lg)', background: 'rgba(244, 67, 54, 0.1)', borderColor: 'var(--color-error)' }}>
                    <div style={{ color: 'var(--color-error)' }}>{error}</div>
                </div>
            )}

            <div style={{ maxWidth: 700 }}>
                {/* Output Settings */}
                <div className="card" style={{ marginBottom: 'var(--space-xl)' }}>
                    <div className="card-header">
                        <h2 className="card-title">Output Settings</h2>
                    </div>

                    <div className="input-group">
                        <label className="input-label">Output Root Folder</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="C:\Users\YourName\Organized Audiobooks"
                            value={outputRoot}
                            onChange={(e) => setOutputRoot(e.target.value)}
                        />
                        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', marginTop: 'var(--space-xs)' }}>
                            Root folder where organized files will be placed
                        </div>
                    </div>
                </div>

                {/* Naming Templates */}
                <div className="card" style={{ marginBottom: 'var(--space-xl)' }}>
                    <div className="card-header">
                        <h2 className="card-title">Naming Templates</h2>
                    </div>

                    <div className="input-group">
                        <label className="input-label">Folder Template</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="{author}/{series_or_title}"
                            value={folderTemplate}
                            onChange={(e) => setFolderTemplate(e.target.value)}
                        />
                        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', marginTop: 'var(--space-xs)' }}>
                            Template for folder structure. Available: {'{author}'}, {'{title}'}, {'{series}'}, {'{series_or_title}'}, {'{year}'}
                        </div>
                    </div>

                    <div className="input-group">
                        <label className="input-label">File Template</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="{title}{part_suffix}"
                            value={fileTemplate}
                            onChange={(e) => setFileTemplate(e.target.value)}
                        />
                        <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)', marginTop: 'var(--space-xs)' }}>
                            Template for file names. Additional: {'{part_suffix}'}, {'{narrator}'}, {'{extension}'}
                        </div>
                    </div>

                    {/* Template Preview */}
                    <div style={{
                        background: 'var(--color-bg-tertiary)',
                        padding: 'var(--space-md)',
                        borderRadius: 'var(--radius-md)',
                        fontSize: 'var(--font-size-sm)',
                        fontFamily: 'monospace',
                    }}>
                        <div style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-xs)' }}>Preview:</div>
                        <div style={{ color: 'var(--color-accent)' }}>
                            {outputRoot || 'C:\\Audiobooks'}\\{folderTemplate || '{author}/{series_or_title}'}\\{fileTemplate || '{title}'}.m4b
                        </div>
                    </div>
                </div>

                {/* Features */}
                <div className="card" style={{ marginBottom: 'var(--space-xl)' }}>
                    <div className="card-header">
                        <h2 className="card-title">Features</h2>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)', cursor: 'pointer' }}>
                            <input
                                type="checkbox"
                                checked={enableLLM}
                                onChange={(e) => setEnableLLM(e.target.checked)}
                                style={{ width: 18, height: 18 }}
                            />
                            <div>
                                <div style={{ fontWeight: 'var(--font-weight-medium)' }}>Enable AI Parsing</div>
                                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                                    Use Gemini AI for advanced filename parsing (requires API key)
                                </div>
                            </div>
                            {settings?.gemini_key_loaded ? (
                                <span className="badge badge-approved">Key Loaded</span>
                            ) : (
                                <span className="badge badge-failed">No Key</span>
                            )}
                        </label>

                        <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)', cursor: 'pointer' }}>
                            <input
                                type="checkbox"
                                checked={enableProviders}
                                onChange={(e) => setEnableProviders(e.target.checked)}
                                style={{ width: 18, height: 18 }}
                            />
                            <div>
                                <div style={{ fontWeight: 'var(--font-weight-medium)' }}>Enable Provider Search</div>
                                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                                    Search Google Books and Audnexus for metadata
                                </div>
                            </div>
                        </label>
                    </div>
                </div>

                {/* API Key Status */}
                <div className="card" style={{ marginBottom: 'var(--space-xl)' }}>
                    <div className="card-header">
                        <h2 className="card-title">API Keys</h2>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <div style={{ fontWeight: 'var(--font-weight-medium)' }}>Gemini API</div>
                                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                                    For AI-powered filename parsing
                                </div>
                            </div>
                            {settings?.gemini_key_loaded ? (
                                <span className="badge badge-approved">Configured</span>
                            ) : (
                                <span className="badge badge-pending">Not Configured</span>
                            )}
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <div style={{ fontWeight: 'var(--font-weight-medium)' }}>Google Books API</div>
                                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                                    For book metadata lookups
                                </div>
                            </div>
                            {settings?.google_books_key_loaded ? (
                                <span className="badge badge-approved">Configured</span>
                            ) : (
                                <span className="badge badge-pending">Not Configured</span>
                            )}
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div>
                                <div style={{ fontWeight: 'var(--font-weight-medium)' }}>Audnexus API</div>
                                <div style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                                    Public API - no key required
                                </div>
                            </div>
                            <span className="badge badge-approved">Available</span>
                        </div>
                    </div>

                    <div style={{
                        marginTop: 'var(--space-lg)',
                        padding: 'var(--space-md)',
                        background: 'var(--color-bg-tertiary)',
                        borderRadius: 'var(--radius-md)',
                        fontSize: 'var(--font-size-sm)',
                        color: 'var(--color-text-muted)',
                    }}>
                        API keys are loaded from text files in <code>C:\Users\mendj\keys\</code>:
                        <ul style={{ marginTop: 'var(--space-sm)', paddingLeft: 'var(--space-lg)' }}>
                            <li><code>gemini_key_local.txt</code></li>
                            <li><code>google_books_api_key.txt</code></li>
                        </ul>
                    </div>
                </div>

                {/* Save Button */}
                <button
                    className="btn btn-primary btn-lg"
                    onClick={handleSave}
                    disabled={saving}
                    style={{ width: '100%' }}
                >
                    {saving ? 'Saving...' : 'Save Settings'}
                </button>
            </div>
        </div>
    );
}
