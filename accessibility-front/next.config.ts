import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
    /* config options here */
    turbopack: {},
    // The dev-only "N" badge defaults to bottom-left, on top of the sidebar's Collapse button.
    devIndicators: { position: 'bottom-right' },
    // Next 16.4 turns on Turbopack's on-disk dev cache by default. Restarting `next dev` on an
    // existing cache put every page into an endless full-reload loop (recompile, reload,
    // recompile...) with no file changing; with the cache off, cold and warm starts are fine.
    experimental: { turbopackFileSystemCacheForDev: false },
};

export default nextConfig;
