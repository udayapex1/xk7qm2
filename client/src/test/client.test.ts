import { afterEach, describe, expect, it, vi } from 'vitest';
import { getMeta } from '../api/client';
afterEach(() => vi.unstubAllGlobals());
describe('API client', () => {
  it('reports backend validation details for non-success responses', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            JSON.stringify({ detail: 'demand_mw must be <= 200000' }),
            { status: 422, headers: { 'Content-Type': 'application/json' } },
          ),
        ),
    );
    await expect(getMeta()).rejects.toMatchObject({
      status: 422,
      message: 'demand_mw must be <= 200000',
    });
  });
  it('reports a friendly backend unreachable message', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('offline')));
    await expect(getMeta()).rejects.toThrow(/Backend unreachable/);
  });
});
