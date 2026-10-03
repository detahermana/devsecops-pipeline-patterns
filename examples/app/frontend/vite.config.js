import { defineConfig } from 'vite';

export default defineConfig({
  build: {
    outDir: 'dist',
    // Fail the build on a sourcemap-less bundle rather than silently shipping
    // one — the pipeline treats a broken build as a gate failure.
    sourcemap: true,
  },
});
