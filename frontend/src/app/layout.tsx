import React from 'react';
import type { Metadata, Viewport } from 'next';
import './global.css';
import { AppProviders } from './providers';

export const metadata: Metadata = {
  title: 'zksato | Risk-First SET/TFEX Trading Control Plane',
  description:
    'Risk-first automated trading control plane for SET/TFEX with paper trading, reconciliation, and video EA research.',
  keywords: [
    'SET trading',
    'TFEX trading',
    'automated trading',
    'zksato',
    'risk-first trading',
    'Settrade',
  ],
  authors: [{ name: 'ZeaZDev' }],
  openGraph: {
    title: 'zksato — Risk-First Trading Control Plane',
    description: 'Risk-first automated trading control plane for SET/TFEX',
    type: 'website',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: [
    { media: '(prefers-color-scheme: dark)', color: '#060913' },
    { media: '(prefers-color-scheme: light)', color: '#f3f4f6' },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning><AppProviders>{children}</AppProviders></body>
    </html>
  );
}
