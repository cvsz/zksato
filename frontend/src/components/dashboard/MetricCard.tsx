"use client";

import React from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subValue?: string;
  trend?: {
    value: string | number;
    positive: boolean;
    text?: string;
  };
  icon: React.ReactNode;
  badge?: {
    text: string;
    variant: 'success' | 'warning' | 'danger' | 'info' | 'primary';
  };
}

export function MetricCard({
  title,
  value,
  subValue,
  trend,
  icon,
  badge,
}: MetricCardProps) {
  return (
    <div className="tailadmin-card tailadmin-metric-card">
      <div className="metric-header">
        <div className="metric-icon-box">
          {icon}
        </div>
        {badge && (
          <span className={`tailadmin-badge badge-${badge.variant}`}>
            {badge.text}
          </span>
        )}
      </div>

      <div className="metric-body">
        <h3 className="metric-value font-mono">{value}</h3>
        <span className="metric-title">{title}</span>
      </div>

      {(trend || subValue) && (
        <div className="metric-footer">
          {trend && (
            <span className={`trend-indicator ${trend.positive ? 'positive' : 'negative'}`}>
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ transform: trend.positive ? 'none' : 'rotate(180deg)' }}
              >
                <polyline points="18 15 12 9 6 15" />
              </svg>
              {trend.value}
            </span>
          )}
          {subValue && (
            <span className="metric-subtext">
              {subValue}
            </span>
          )}
        </div>
      )}
    </div>
  );
}
