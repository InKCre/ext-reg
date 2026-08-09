import { defineConfig } from 'tsdown'

export default defineConfig({
  entry: ['src/index.ts'],
  format: 'esm',
  platform: 'neutral',
  target: 'es2022',
  clean: true,
  sourcemap: true,
  treeshake: true,
  deps: {
    neverBundle: true,
  },
  dts: {
    generator: 'tsc',
    resolver: 'tsc',
    sourcemap: true,
  },
})
