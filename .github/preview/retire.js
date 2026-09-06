// Temporarily replaces the closed PR's Worker. Never bundled with Registry.
export default {
  async fetch(request, env) {
    if (
      request.method !== 'POST' ||
      request.headers.get('Authorization') !== `Bearer ${env.RETIRE_TOKEN}`
    ) {
      return new Response('This pull-request preview is no longer active.', {
        status: 410,
        headers: { 'Cache-Control': 'no-store' },
      })
    }
    const batch = await env.ARTIFACTS.list({ limit: 1000 })
    if (batch.objects.length) {
      await env.ARTIFACTS.delete(batch.objects.map((object) => object.key))
    }
    return Response.json({ deleted: batch.objects.length })
  },
}
