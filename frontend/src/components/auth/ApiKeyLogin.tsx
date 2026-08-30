"use client";

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';

interface ApiKeyLoginProps {
  onSuccess?: (user: unknown) => void;
  onError?: (error: string) => void;
}

export function ApiKeyLogin({ onSuccess, onError }: ApiKeyLoginProps) {
  const { t } = useTranslation();
  const [apiKey, setApiKey] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    setLoading(true);
    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:9569';
      const response = await fetch(`${backendUrl}/v1/auth/session`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': apiKey,
        },
      });
      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || `Authentication failed (${response.status})`);
      }
      sessionStorage.setItem('zksato_api_key', apiKey);
      if (onSuccess) {
        onSuccess(null);
      }
    } catch (error) {
      console.error('API key login error:', error);
      if (onError) {
        onError(
          error instanceof Error ? error.message : 'Sign-in failed',
        );
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); handleLogin(); }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        width: '100%',
      }}
    >
      <input
        type="password"
        value={apiKey}
        onChange={(e) => setApiKey(e.target.value)}
        placeholder="Enter API key"
        required
        disabled={loading}
        style={{
          width: '100%',
          padding: '12px 16px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-input)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--text-primary)',
          fontSize: '14px',
        }}
      />
      <button
        type="submit"
        disabled={loading || !apiKey.trim()}
        aria-label={loading ? 'Connecting...' : 'Sign in with API key'}
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
          width: '100%',
          padding: '12px 24px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border-input)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--text-primary)',
          fontSize: '16px',
          fontWeight: '600',
          cursor: loading || !apiKey.trim() ? 'not-allowed' : 'pointer',
          opacity: loading ? 0.6 : 1,
          transition: 'var(--transition-smooth)',
        }}
      >
        {loading ? 'Authenticating...' : 'Sign In with API Key'}
      </button>
    </form>
  );
}
