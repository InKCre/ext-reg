import { defineConfig } from '@hey-api/openapi-ts'

export default defineConfig({
  input: '../../contracts/openapi.json',
  output: {
    path: 'src/generated',
    clean: true,
  },
  plugins: ['@hey-api/typescript', '@hey-api/sdk', 'zod'],
})
