import { useCallback, useEffect, useRef, useState } from 'react';
import { getElementUnderPointer } from '../utils/extractUIElements';

export interface PointerState {
  x: number;
  y: number;
  element_id: string | null;
}

export function usePointerTracking(onTargetChange?: (id: string | null) => void) {
  const [pointer, setPointer] = useState<PointerState>({ x: 0, y: 0, element_id: null });
  const rafRef = useRef<number>();

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(() => {
        const element_id = getElementUnderPointer(e.clientX, e.clientY);
        setPointer({ x: e.clientX, y: e.clientY, element_id });
        onTargetChange?.(element_id);
      });
    };
    window.addEventListener('mousemove', onMove, { passive: true });
    return () => {
      window.removeEventListener('mousemove', onMove);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [onTargetChange]);

  const getSnapshot = useCallback(() => pointer, [pointer]);

  return { pointer, getSnapshot };
}
