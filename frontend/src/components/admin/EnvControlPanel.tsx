"use client";

import React, { useState, useEffect } from 'react';
import { getBackendUrl } from '../../utils/api';

interface EnvItem {
  key: string;
  value: string;
  is_secret: boolean;
  is_configured: boolean;
}

export function EnvControlPanel() {
  const backendUrl = getBackendUrl();
  const [items, setItems] = useState<EnvItem[]>([]);
  const [rawText, setRawText] = useState<string>('');
  const [mode, setMode] = useState<'form' | 'raw'>('form');
  const [search, setSearch] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [revealedSecrets, setRevealedSecrets] = useState<Record<string, boolean>>({});
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [statusMsg, setStatusMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const fetchEnv = async () => {
    setLoading(true);
    setStatusMsg(null);
    try {
      const res = await fetch(`${backendUrl}/v1/admin/env`);
      if (!res.ok) {
        throw new Error(`Failed to load .env: ${res.statusText}`);
      }
      const data = await res.json();
      setItems(data.items || []);
      setRawText(data.raw || '');
      const initialForm: Record<string, string> = {};
      (data.items || []).forEach((item: EnvItem) => {
        initialForm[item.key] = item.value;
      });
      setFormValues(initialForm);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setStatusMsg({ text: msg, type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEnv();
  }, [backendUrl]);

  const handleSaveForm = async () => {
    setSaving(true);
    setStatusMsg(null);
    try {
      const res = await fetch(`${backendUrl}/v1/admin/env`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formValues),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Save failed');
      }
      const result = await res.json();
      setStatusMsg({ text: `Successfully updated ${result.count || 0} settings in .env! (Backup created at .env.bak)`, type: 'success' });
      await fetchEnv();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setStatusMsg({ text: msg, type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const handleSaveRaw = async () => {
    setSaving(true);
    setStatusMsg(null);
    try {
      const res = await fetch(`${backendUrl}/v1/admin/env/raw`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: rawText }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Save failed');
      }
      setStatusMsg({ text: 'Raw .env saved successfully! (Backup created at .env.bak)', type: 'success' });
      await fetchEnv();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      setStatusMsg({ text: msg, type: 'error' });
    } finally {
      setSaving(false);
    }
  };

  const toggleReveal = (key: string) => {
    setRevealedSecrets((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const filteredItems = items.filter((item) =>
    item.key.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="glass-card" style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 className="h3 font-mono" style={{ margin: 0 }}>.env Configuration Control Panel</h2>
          <p style={{ margin: '4px 0 0 0', color: 'var(--text-muted)', fontSize: '13px' }}>
            Manage server environment variables safely. Sensitive credentials are protected and backed up automatically on update.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            className={`btn-base ${mode === 'form' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setMode('form')}
            style={{ fontSize: '13px', padding: '6px 14px' }}
          >
            Form View
          </button>
          <button
            className={`btn-base ${mode === 'raw' ? 'btn-primary' : 'btn-ghost'}`}
            onClick={() => setMode('raw')}
            style={{ fontSize: '13px', padding: '6px 14px' }}
          >
            Raw Editor
          </button>
          <button
            className="btn-base btn-ghost"
            onClick={fetchEnv}
            disabled={loading}
            style={{ fontSize: '13px', padding: '6px 14px' }}
          >
            Reload
          </button>
        </div>
      </div>

      {statusMsg && (
        <div
          role="alert"
          style={{
            padding: '12px 16px',
            borderRadius: 'var(--radius-md)',
            background: statusMsg.type === 'success' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
            border: `1px solid ${statusMsg.type === 'success' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            color: statusMsg.type === 'success' ? '#10b981' : '#ef4444',
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
          }}
        >
          <span>{statusMsg.type === 'success' ? '✓' : '⚠'}</span>
          <span>{statusMsg.text}</span>
        </div>
      )}

      {mode === 'form' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
            <input
              type="text"
              placeholder="Search variables (e.g. SETTRADE, TELEGRAM, RISK)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-base"
              style={{ maxWidth: '400px', width: '100%', fontSize: '13px' }}
            />
            <button
              className="btn-base btn-primary"
              onClick={handleSaveForm}
              disabled={saving}
              style={{ padding: '8px 20px', fontWeight: 600 }}
            >
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>

          <div style={{ overflowX: 'auto', border: '1px solid rgba(255,255,255,0.08)', borderRadius: 'var(--radius-lg)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '13px' }}>
              <thead>
                <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
                  <th style={{ padding: '12px 16px', width: '35%' }}>Variable Key</th>
                  <th style={{ padding: '12px 16px' }}>Configured Value</th>
                  <th style={{ padding: '12px 16px', width: '15%' }}>Type</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => {
                  const isRevealed = revealedSecrets[item.key];
                  return (
                    <tr key={item.key} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '10px 16px', fontFamily: 'monospace', fontWeight: 600, color: 'var(--text-primary)' }}>
                        {item.key}
                      </td>
                      <td style={{ padding: '10px 16px' }}>
                        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                          <input
                            type={item.is_secret && !isRevealed ? 'password' : 'text'}
                            value={formValues[item.key] ?? ''}
                            onChange={(e) => {
                              const val = e.target.value;
                              setFormValues((prev) => ({ ...prev, [item.key]: val }));
                            }}
                            className="input-base"
                            style={{ flex: 1, fontFamily: 'monospace', fontSize: '13px' }}
                          />
                          {item.is_secret && (
                            <button
                              type="button"
                              className="btn-base btn-ghost"
                              onClick={() => toggleReveal(item.key)}
                              style={{ padding: '6px 10px', fontSize: '12px' }}
                              title={isRevealed ? 'Hide Secret' : 'Reveal Secret'}
                            >
                              {isRevealed ? 'Hide' : 'Show'}
                            </button>
                          )}
                        </div>
                      </td>
                      <td style={{ padding: '10px 16px' }}>
                        {item.is_secret ? (
                          <span className="badge badge-warning" style={{ fontSize: '11px' }}>Secret / Credential</span>
                        ) : (
                          <span className="badge badge-accent" style={{ fontSize: '11px' }}>Config Param</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
                {filteredItems.length === 0 && !loading && (
                  <tr>
                    <td colSpan={3} style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>
                      No environment variables match the search filter.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
              Directly edit raw <code>.env</code> file. Formats with comments and blank lines are fully preserved.
            </span>
            <button
              className="btn-base btn-primary"
              onClick={handleSaveRaw}
              disabled={saving}
              style={{ padding: '8px 20px', fontWeight: 600 }}
            >
              {saving ? 'Saving...' : 'Save Raw .env'}
            </button>
          </div>
          <textarea
            value={rawText}
            onChange={(e) => setRawText(e.target.value)}
            rows={22}
            style={{
              width: '100%',
              fontFamily: 'monospace',
              fontSize: '13px',
              padding: '16px',
              background: 'rgba(0,0,0,0.4)',
              color: '#f8fafc',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 'var(--radius-lg)',
              resize: 'vertical',
              lineHeight: 1.5,
            }}
          />
        </div>
      )}
    </div>
  );
}
