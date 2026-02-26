import { withSentryConfig } from '@sentry/nextjs';

/** @type {import('next').NextConfig} */
const isDevelopment = process.env.NODE_ENV === 'development';

const nextConfig = {
  distDir: isDevelopment ? (process.env.NEXT_DEV_DIST_DIR || '.next-dev') : '.next',
  output: 'standalone',
  serverExternalPackages: ['playwright'],
  images: {
    remotePatterns: [
      // Local development
      {
        protocol: 'http',
        hostname: 'localhost',
      },
      {
        protocol: 'http',
        hostname: '127.0.0.1',
      },
      {
        protocol: 'https',
        hostname: 'localhost',
      },
      {
        protocol: 'https',
        hostname: '127.0.0.1',
      },
      // Russian marketplaces
      {
        protocol: 'https',
        hostname: '*.wb.ru',
      },
      {
        protocol: 'https',
        hostname: '*.wildberries.ru',
      },
      {
        protocol: 'https',
        hostname: 'ozon.ru',
      },
      {
        protocol: 'https',
        hostname: '*.ozon.ru',
      },
      {
        protocol: 'https',
        hostname: 'lamoda.ru',
      },
      {
        protocol: 'https',
        hostname: '*.lamoda.ru',
      },
      {
        protocol: 'https',
        hostname: 'dns-shop.ru',
      },
      {
        protocol: 'https',
        hostname: '*.dns-shop.ru',
      },
      // International marketplaces
      {
        protocol: 'https',
        hostname: 'amazon.com',
      },
      {
        protocol: 'https',
        hostname: '*.amazon.com',
      },
      {
        protocol: 'https',
        hostname: 'amazon.ru',
      },
      {
        protocol: 'https',
        hostname: '*.amazon.ru',
      },
      {
        protocol: 'https',
        hostname: 'aliexpress.com',
      },
      {
        protocol: 'https',
        hostname: '*.aliexpress.com',
      },
      {
        protocol: 'https',
        hostname: 'aliexpress.ru',
      },
      {
        protocol: 'https',
        hostname: '*.aliexpress.ru',
      },
      // Yandex
      {
        protocol: 'https',
        hostname: 'market.yandex.ru',
      },
      {
        protocol: 'https',
        hostname: '*.yandex.ru',
      },
      // SECURITY: Removed wildcard hostname '**' to prevent loading images from arbitrary domains.
      // User-provided image URLs should be proxied through the backend to validate safety.
      // If you need to allow additional domains, add them explicitly above.
    ],
  },
  async rewrites() {
    const backendBase =
      process.env.NEXT_PUBLIC_API_BASE_URL ||
      process.env.NEXT_PUBLIC_BACKEND_URL ||
      process.env.BACKEND_URL ||
      'http://localhost:8000';
    return [
      {
        source: '/api/:path*',
        destination: `${backendBase}/:path*`,
      },
      {
        source: '/ws/:path*',
        destination: `${backendBase}/ws/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/sw.js',
        headers: [
          {
            key: 'Service-Worker-Allowed',
            value: '/',
          },
          {
            key: 'Cache-Control',
            value: 'public, max-age=0, must-revalidate',
          },
          {
            key: 'Content-Type',
            value: 'application/javascript; charset=utf-8',
          },
        ],
      },
      {
        source: '/manifest.json',
        headers: [
          {
            key: 'Content-Type',
            value: 'application/manifest+json',
          },
          {
            key: 'Cache-Control',
            value: 'public, max-age=86400',
          },
        ],
      },
      {
        source: '/icons/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
      {
        source: '/splash/:path*',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable',
          },
        ],
      },
    ];
  },
};

// Wrap with Sentry only if DSN is configured (optional integration)
const sentryConfig = {
  org: process.env.SENTRY_ORG,
  project: process.env.SENTRY_PROJECT,
  silent: !process.env.NEXT_PUBLIC_SENTRY_DSN, // Silent if no DSN configured
  widenClientFileUpload: true,
  hideSourceMaps: true,
};

export default withSentryConfig(nextConfig, sentryConfig);

