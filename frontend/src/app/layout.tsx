import React from 'react';
import type { Metadata, Viewport } from 'next';
import { Outfit, JetBrains_Mono } from 'next/font/google';
import './global.css';

const outfit = Outfit({
  subsets: ['latin'],
  weight: ['300', '400', '500', '600', '700', '800'],
  variable: '--font-outfit',
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
  variable: '--font-mono',
  display: 'swap',
});

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
    <html lang="en" className={`${outfit.variable} ${jetbrainsMono.variable}`} suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
