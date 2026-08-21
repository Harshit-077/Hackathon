import { describe, it, expect } from 'vitest';
import { extractUIElements } from '../utils/extractUIElements';

describe('extractUIElements', () => {
  it('extracts intent metadata from DOM', () => {
    document.body.innerHTML = `
      <div data-intent-id="revenue" data-intent-label="Revenue" data-intent-type="metric_card">
        <span data-intent-value>$1.24M</span>
      </div>`;
    const els = extractUIElements();
    expect(els).toHaveLength(1);
    expect(els[0].id).toBe('revenue');
    expect(els[0].value).toBe('$1.24M');
  });
});
