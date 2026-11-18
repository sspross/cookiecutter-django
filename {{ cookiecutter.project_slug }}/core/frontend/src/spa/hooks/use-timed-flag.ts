import { useCallback, useEffect, useRef, useState } from "react";

export function useTimedFlag(durationMs: number): [boolean, () => void] {
  const [isRaised, setIsRaised] = useState(false);
  const pendingReset = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  useEffect(() => () => clearTimeout(pendingReset.current), []);

  const raise = useCallback(() => {
    clearTimeout(pendingReset.current);
    setIsRaised(true);
    pendingReset.current = setTimeout(() => setIsRaised(false), durationMs);
  }, [durationMs]);

  return [isRaised, raise];
}
