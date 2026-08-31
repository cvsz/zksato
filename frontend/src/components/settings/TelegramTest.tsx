"use client";

import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { getBackendUrl } from '../../utils/api';

export function TelegramTest() {
  const { t } = useTranslation();
  const [message, setMessage] = useState('zksato test notification');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const backendUrl = getBackendUrl();

  const handleTest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${backendUrl}/v1/telegram/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message }),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && data.sent) {
        setResult({ type: 'success', text: t('telegram.test_sent') });
      } else {
        setResult({ type: 'error', text: t('telegram.test_failed') });
      }
    } catch {
      setResult({ type: 'error', text: t('telegram.test_failed') });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="glass-card-static animate-fade-in">
      <h3 className="h3" style={{ marginBottom: '20px' }}>
        {t('telegram.title')}
      </h3>

      <p className="text-secondary" style={{ marginBottom: '20px', fontSize: '14px', lineHeight: '1.5' }}>
        {t('telegram.desc')}
      </p>

      <form onSubmit={handleTest}>
        <div className="form-group" style={{ marginBottom: '16px' }}>
          <label className="form-label">{t('telegram.chat_id_label')}</label>
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={t('telegram.chat_id_placeholder')}
            className="input-field"
            required
          />
          <p className="text-muted" style={{ fontSize: '12px', marginTop: '6px' }}>
            {t('telegram.find_chat_id_hint')}
          </p>
        </div>

          <button type="submit" disabled={loading} className="btn-base btn-primary">
            {loading ? t('telegram.linking') : t('telegram.test_button')}
          </button>
      </form>

      {result && (
        <div
          role="alert"
          className={`badge ${result.type === 'success' ? 'badge-accent' : 'badge-danger'}`}
          style={{
            display: 'flex',
            marginTop: '16px',
            padding: '10px 14px',
            borderRadius: 'var(--radius-md)',
          }}
        >
          <span>{result.text}</span>
        </div>
      )}
    </div>
  );
}
