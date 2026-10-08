/** @type {import('next').NextConfig} */
const apiTarget = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
      },
    ],
  },
  async rewrites() {
    return [
      {
        source: "/backend/:path*",
        destination: `${apiTarget}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
