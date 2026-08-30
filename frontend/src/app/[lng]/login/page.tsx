"use client";

import React, { useState } from 'react';
import { initI18n } from '../../i18n/client';
import { useTranslation } from 'react-i18next';
import { usePathname, useRouter } from 'next/navigation';
import { getBackendUrl } from '../../../utils/api';

export default function LoginPage() {
  const pathname = usePathname();
  const lng = pathname?.split('/')[1] || 'en';
  initI18n(lng);
  const { t } = useTranslation('translation');
  const router = useRouter();
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const backendUrl = getBackendUrl();
      const res = await fetch(`${backendUrl}/v1/auth/session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Authentication failed (${res.status})`);
      }
      const data = await res.json();
      sessionStorage.setItem('zksato_api_key', apiKey);
      router.push(`/${lng}/dashboard`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <div
        className="bg-orb"
        style={{
          position: 'fixed',
          top: '-25%',
          right: '-15%',
          width: '700px',
          height: '700px',
          background:
            'radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%)',
          borderRadius: '50%',
          pointerEvents: 'none',
        }}
      />
      <div
        className="bg-orb"
        style={{
          position: 'fixed',
          bottom: '-25%',
          left: '-15%',
          width: '600px',
          height: '600px',
          background:
            'radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%)',
          borderRadius: '50%',
          pointerEvents: 'none',
        }}
      />

      <div
        className="glass-card-static animate-fade-in"
        style={{
          maxWidth: '440px',
          width: '100%',
          textAlign: 'center',
        padding: 'clamp(28px, 8vw, 48px) clamp(20px, 6vw, 36px)',
        margin: '0 clamp(12px, 4vw, 20px)',
          position: 'relative',
        }}
      >
        <div style={{ marginBottom: '36px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '64px',
              height: '64px',
              borderRadius: '18px',
              background: 'var(--color-primary-bg)',
              border: '1px solid var(--color-primary-border)',
              marginBottom: '20px',
              boxShadow: 'var(--shadow-glow-primary)',
            }}
          >
            <div
              style={{
                width: '18px',
                height: '18px',
                borderRadius: '50%',
                background: 'var(--color-primary)',
                boxShadow: '0 0 12px var(--color-primary)',
              }}
            />
          </div>
          <h1
            className="h1"
            style={{ marginBottom: '8px', letterSpacing: '-0.02em' }}
          >
            z<span className="text-primary-color">ksato</span>
          </h1>
          <p className="text-secondary" style={{ fontSize: '15px' }}>
            {t('login.subtitle')}
          </p>
        </div>

        <form onSubmit={handleLogin} style={{ marginBottom: '32px' }}>
          <div className="form-group" style={{ marginBottom: '16px', textAlign: 'left' }}>
            <label className="form-label">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="Enter your API key"
              className="input-field"
              required
              autoFocus
            />
          </div>
          {error && (
            <div
              style={{
                marginBottom: '16px',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(239,68,68,0.08)',
                border: '1px solid rgba(239,68,68,0.25)',
                color: 'var(--color-danger)',
                fontSize: '13px',
              }}
            >
              {error}
            </div>
          )}
          <button
            type="submit"
            disabled={loading || !apiKey.trim()}
            className="btn-base btn-primary btn-full btn-lg"
            style={{
              opacity: loading ? 0.6 : 1,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}
          >
            {loading ? 'Authenticating...' : 'Sign In'}
          </button>
        </form>

        <div className="divider" />
        <p
          className="text-muted"
          style={{ fontSize: '13px', lineHeight: '1.6', marginTop: '20px' }}
        >
          {t('login.disclaimer')}
        </p>
      </div>
    </div>
  );
}
