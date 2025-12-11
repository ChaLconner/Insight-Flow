import { useEffect, useState } from 'react';

/**
 * Hook to delay rendering of non-critical components until after the main content has loaded.
 * This helps in reducing Total Blocking Time (TBT) by splitting hydration work.
 */
export function useInteractionReady(delay = 1000) {
    const [isReady, setIsReady] = useState(false);

    useEffect(() => {
        const timer = setTimeout(() => {
            setIsReady(true);
        }, delay);

        return () => clearTimeout(timer);
    }, [delay]);

    return isReady; // Return simple boolean
}
