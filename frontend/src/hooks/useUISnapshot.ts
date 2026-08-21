import { useCallback, useEffect, useRef } from 'react';
import { extractUIElements } from '../utils/extractUIElements';
import type { UIElement } from '../types/contract';

export function useUISnapshot() {
  const cacheRef = useRef<UIElement[]>([]);

  const snapshot = useCallback((): UIElement[] => {
    cacheRef.current = extractUIElements();
    return cacheRef.current;
  }, []);

  useEffect(() => {
    const onResize = () => { cacheRef.current = extractUIElements(); };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return { snapshot, elements: cacheRef };
}
