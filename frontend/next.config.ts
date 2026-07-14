import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // required by frontend/Dockerfile for deployment
};

export default nextConfig;
