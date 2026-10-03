import { describe, expect, it } from 'vitest';
import { formatItem } from '../src/api.js';

describe('formatItem', () => {
  it('renders id and name', () => {
    expect(formatItem({ id: 1, name: 'widget' })).toBe('1: widget');
  });

  it('handles an empty name', () => {
    expect(formatItem({ id: 2, name: '' })).toBe('2: ');
  });
});
