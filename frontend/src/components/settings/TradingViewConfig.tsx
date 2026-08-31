"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { getBackendUrl } from '../../utils/api';

interface TVWebhook {
  symbol: string;
  exchange?: string;
  created_at?: string;
}

export function TradingViewConfig() {
  const { t } = useTranslation();
  const [webhooks, setWebhooks] = useState<TVWebhook[]>([]);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState(false);

  const backendUrl = getBackendUrl();
  const webhookUrl = `${backendUrl}/v1/tradingview/webhook`;

  const fetchWebhooks = useCallback(async () => {
    try {
      setError(false);
      const res = await fetch(`${backendUrl}/v1/tradingview/config`);
      if (res.ok) {
        const data = await res.json();
        const items = Array.isArray(data?.items) ? data.items : [];
        setWebhooks(
          items.map((item: any) => ({
            symbol: item.symbol || '',
            exchange: item.exchange || '',
            created_at: item.created_at,
          })),
        );
      } else {
        setError(true);
      }
    } catch {
      setError(true);
    }
  }, [backendUrl]);

  useEffect(() => {
    fetchWebhooks();
    const interval = setInterval(fetchWebhooks, 5000);
    return () => clearInterval(interval);
  }, [backendUrl, fetchWebhooks]);

  const handleCopy = () => {
    navigator.clipboard.writeText(webhookUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="glass-card-static animate-fade-in">
      <h3 className="h3" style={{ marginBottom: '16px' }}>
        {t('tradingview.title')}
      </h3>

      <p
        className="text-secondary"
        style={{
          fontSize: '14px',
          lineHeight: '1.5',
          marginBottom: '20px',
        }}
      >
        {t('tradingview.desc')}
      </p>

      <div style={{ marginBottom: '24px' }}>
        <div className="form-group">
          <label className="form-label">{t('tradingview.webhook_url')}</label>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-input)',
              borderRadius: 'var(--radius-md)',
              padding: '8px 12px',
            }}
          >
            <code
              className="font-mono"
              style={{
                fontSize: '13px',
                color: 'var(--color-primary)',
                overflowX: 'auto',
                flex: 1,
                whiteSpace: 'nowrap',
              }}
            >
              {webhookUrl}
            </code>
            <button
              onClick={handleCopy}
              className="btn-base btn-sm"
              style={{
                marginLeft: '10px',
                color: copied
                  ? 'var(--color-accent)'
                  : 'var(--color-primary)',
              }}
            >
              {copied ? t('tradingview.copied') : t('tradingview.copy')}
            </button>
          </div>
        </div>

        <div
          style={{
            padding: '14px',
            background: 'var(--color-warning-bg)',
            border: '1px solid rgba(245, 158, 11, 0.2)',
            borderRadius: 'var(--radius-md)',
            fontSize: '13px',
            lineHeight: '1.5',
            color: 'var(--color-warning)',
          }}
        >
          <strong>{t('tradingview.required_header')}</strong>
          <code
            className="font-mono"
            style={{
              display: 'block',
              background: 'rgba(0,0,0,0.2)',
              padding: '6px 10px',
              borderRadius: 'var(--radius-sm)',
              marginTop: '6px',
              color: 'var(--text-primary)',
            }}
          >
            X-Webhook-Secret: &lt;your-webhook-secret-token&gt;
          </code>
        </div>
      </div>

      <div>
        <h4 className="h4" style={{ marginBottom: '12px' }}>
          {t('tradingview.webhook_configs', 'Webhook Configurations')}
        </h4>
        <div
          aria-live="polite"
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            maxHeight: '160px',
            overflowY: 'auto',
          }}
        >
          {webhooks.map((wh) => (
            <div
              key={wh.symbol}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                fontSize: '13px',
              }}
            >
              <div>
                <strong style={{ marginRight: '8px' }}>{wh.symbol}</strong>
                <span className="text-muted">{wh.exchange || 'default'}</span>
              </div>
              <span className="text-secondary">
                {wh.created_at ? new Date(wh.created_at).toLocaleString() : ''}
              </span>
            </div>
          ))}
          {webhooks.length === 0 && !error && (
            <div
              className="text-muted"
              style={{
                textAlign: 'center',
                padding: '16px',
                fontSize: '13px',
              }}
            >
              {t('tradingview.no_alerts')}
            </div>
          )}
          {error && (
            <div
              style={{
                textAlign: 'center',
                padding: '16px',
                fontSize: '13px',
              }}
            >
              <span className="text-muted" style={{ display: 'block', marginBottom: '8px' }}>
                Failed to load webhook configs
              </span>
              <button
                onClick={fetchWebhooks}
                className="btn-base btn-sm"
                style={{ color: 'var(--color-primary)' }}
              >
                Retry
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
