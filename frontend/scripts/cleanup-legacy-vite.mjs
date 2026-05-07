import { rmSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

// The project is now a Next.js App Router frontend. Because the ZIP workflow
// overlays files on Windows, old Vite entrypoints can remain on disk and confuse
// Next's route discovery. This cleanup removes only obsolete V1/Vite paths.
const projectRoot = process.cwd();
const legacyPaths = ['src/pages', 'src/App.jsx', 'src/main.jsx', 'src/styles', 'vite.config.js', 'index.html'];

for (const relativePath of legacyPaths) {
  const absolutePath = resolve(projectRoot, relativePath);
  if (existsSync(absolutePath)) {
    rmSync(absolutePath, { recursive: true, force: true });
    console.log(`[cleanup-next] Removed legacy Vite path: ${relativePath}`);
  }
}
