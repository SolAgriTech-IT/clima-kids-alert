/** @type {import('next').NextConfig} */
const staticExport = process.env.NEXT_STATIC_EXPORT === "1";

const nextConfig = {
  output: staticExport ? "export" : "standalone",
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  images: { unoptimized: true },
};

export default nextConfig;
