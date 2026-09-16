import { normalizeApiBaseUrl } from './api';

describe('normalizeApiBaseUrl', () => {
  it('uses a same-origin API path by default', () => {
    expect(normalizeApiBaseUrl()).toBe('/api/v1');
  });

  it('adds the API path to a host-only override', () => {
    expect(normalizeApiBaseUrl('http://localhost:8002')).toBe('http://localhost:8002/api/v1');
  });

  it('does not duplicate an existing API path', () => {
    expect(normalizeApiBaseUrl('https://example.test/api/v1/')).toBe('https://example.test/api/v1');
  });
});
