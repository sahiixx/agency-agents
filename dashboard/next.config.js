/** @type {import('next').NextConfig} */
const nextConfig = {
  // Proxy API calls to the Agency A2A server (default port 8100)
  async rewrites() {
    const agencyUrl = process.env.AGENCY_A2A_URL || 'http://localhost:8100';
    return [
      {
        source:      '/api/agency/:path*',
        destination: `${agencyUrl}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
