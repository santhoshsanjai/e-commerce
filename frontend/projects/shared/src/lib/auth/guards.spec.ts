import { safeReturnUrl } from './guards';

describe('safeReturnUrl', () => {
  it('keeps same-site paths', () => {
    expect(safeReturnUrl('/orders?page=2')).toBe('/orders?page=2');
  });

  it('falls back to home for missing or off-site targets', () => {
    for (const bad of [
      undefined,
      null,
      '',
      'https://evil.example',
      '//evil.example',
      '/\\evil.example',
      'javascript:alert(1)',
    ]) {
      expect(safeReturnUrl(bad)).toBe('/');
    }
  });
});
