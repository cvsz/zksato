/** @type {import('next').NextConfig} */
const path = require('path');

const nextConfig = {
  output: 'standalone',
  outputFileTracingRoot: path.join(__dirname),
  reactStrictMode: true,
  poweredByHeader: false,

  turbopack: {
    root: path.join(__dirname),
  },

  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'X-XSS-Protection', value: '1; mode=block' },
          { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://s3.tradingview.com https://*.tradingview.com",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "img-src 'self' data: blob: https:",
              "font-src 'self' data: https://fonts.gstatic.com",
              "connect-src 'self' https: http://localhost:* ws: wss: https://*.tradingview.com",
              "frame-src 'self' https://zksato-api.zeaz.dev http://localhost:* https://*.tradingview.com",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join('; '),
          },
        ],
      },
    ];
  },
}

module.exports = nextConfig
