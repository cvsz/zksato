import React from 'react';
import type { Metadata, Viewport } from 'next';
import './global.css';

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
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
