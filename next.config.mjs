/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'www.nikkansports.com',
      },
    ],
  },
  // 二重構造を防ぐための設定
  reactStrictMode: true,
  // OneDriveの日本語パス問題を回避するため、experimental設定を追加
  experimental: {
    // シンボリックリンクの問題を回避
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
  // 出力先を明示的に設定（OneDriveの同期問題を回避）
  distDir: '.next',
}

export default nextConfig
