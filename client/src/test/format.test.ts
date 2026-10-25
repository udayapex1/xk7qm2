import { describe, expect, it } from 'vitest';
import { formatBias, formatNumber, formatTime } from '../lib/format';
describe('format helpers', () => {
  it('formats MW values and signed bias', () => {
    expect(formatNumber(12345.6, 'MW')).toBe('12,345.6 MW');
    expect(formatBias(12)).toBe('+12 MW');
    expect(formatBias(-12)).toBe('-12 MW');
  });
  it('shows London local time and UTC in timestamp details', () => {
    expect(formatTime('2026-01-04T00:00:00Z', true)).toContain(
      '00:00 London · UTC 00:00',
    );
  });
});
