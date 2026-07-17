import { describe, it, expect } from 'vitest'
// Vite-native file access (no node builtins — the app tsconfig has no
// node types, and CI type-checks with `tsc -b`).
import manifestRaw from '../../public/manifest.webmanifest?raw'

const pngs = import.meta.glob('../../public/*.png', {
  eager: true,
  query: '?url',
  import: 'default',
})
const swFiles = import.meta.glob('../../public/sw.js', {
  eager: true,
  query: '?raw',
  import: 'default',
})

describe('PWA assets (WP19b)', () => {
  it('manifest is valid JSON with the installability essentials', () => {
    const manifest = JSON.parse(manifestRaw)
    expect(manifest.name).toBe('PolyglotSRS')
    expect(manifest.display).toBe('standalone')
    expect(manifest.start_url).toBe('/')
    const sizes = manifest.icons.map((i: { sizes: string }) => i.sizes)
    expect(sizes).toContain('192x192')
    expect(sizes).toContain('512x512')
    expect(
      manifest.icons.some((i: { purpose?: string }) => i.purpose === 'maskable'),
    ).toBe(true)
  })

  it('every icon the manifest references exists', () => {
    const manifest = JSON.parse(manifestRaw)
    const have = Object.keys(pngs)
    for (const icon of manifest.icons as { src: string }[]) {
      expect(
        have.some((k) => k.endsWith(icon.src)),
        icon.src,
      ).toBe(true)
    }
    expect(have.some((k) => k.endsWith('/apple-touch-icon.png'))).toBe(true)
    expect(Object.keys(swFiles).length).toBe(1)
  })
})
