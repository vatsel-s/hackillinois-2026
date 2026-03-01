/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Proxy API to backend (run: uvicorn backend.main:app --reload --port 8000)
  async rewrites() {
    return [
      { source: "/api/proxy/:path*", destination: "http://127.0.0.1:8000/api/:path*" },
    ];
  },
};

module.exports = nextConfig;
