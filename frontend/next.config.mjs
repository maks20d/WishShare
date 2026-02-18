/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  serverExternalPackages: ['playwright'],
  images: {
    remotePatterns: [
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
};

export default nextConfig;
