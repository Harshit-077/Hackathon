import type { UIElement } from '../types/contract';

const INTENT_SELECTOR = '[data-intent-id]';

export function extractUIElements(root: Document | Element = document): UIElement[] {
  const nodes = root.querySelectorAll(INTENT_SELECTOR);
  const elements: UIElement[] = [];

  nodes.forEach((node) => {
    const el = node as HTMLElement;
    const id = el.dataset.intentId;
    const label = el.dataset.intentLabel;
    const type = el.dataset.intentType;
    if (!id || !label || !type) return;

    const rect = el.getBoundingClientRect();
    const valueEl = el.querySelector('[data-intent-value]');
    const value = valueEl?.textContent?.trim() ?? el.dataset.intentValue ?? null;

    elements.push({
      id,
      label,
      type,
      bbox: { x: rect.x, y: rect.y, w: rect.width, h: rect.height },
      value,
    });
  });

  return elements;
}

export function getElementUnderPointer(x: number, y: number): string | null {
  const el = document.elementFromPoint(x, y);
  if (!el) return null;
  const intentEl = el.closest(INTENT_SELECTOR) as HTMLElement | null;
  return intentEl?.dataset.intentId ?? null;
}
