'use client';
import { useSearchParams } from 'next/navigation';
import { useCallback } from 'react';

/**
 * List filters kept in the URL query string, so they survive navigating away and back,
 * a reload, and can be shared as a link.
 *
 * Writes go through window.history.replaceState, which Next.js syncs with
 * useSearchParams without a server round trip. replace (not push) keeps each filter
 * change out of the history stack: Back returns to the previous page, not to the
 * previous filter.
 */
export function useUrlFilters() {
    const params = useSearchParams();

    const setFilters = useCallback((changes: Record<string, string | null | undefined>) => {
        const next = new URLSearchParams(window.location.search);
        for (const [key, value] of Object.entries(changes)) {
            if (value) {
                next.set(key, value);
            } else {
                next.delete(key);
            }
        }
        const query = next.toString();
        window.history.replaceState(
            null,
            '',
            `${window.location.pathname}${query ? `?${query}` : ''}${window.location.hash}`
        );
    }, []);

    return { params, setFilters };
}

/** A positive page number from a query value, defaulting to 1. */
export function pageParam(value: string | null): number {
    const page = Number(value);
    return Number.isInteger(page) && page > 0 ? page : 1;
}
