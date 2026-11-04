import { defineConfig } from 'tsdown'

export default defineConfig({
  entry: ['src/index.ts'],
  format: ['esm'],
  clean: true,
  external: ['@inkcre/core', '@module-federation/runtime'],
})
