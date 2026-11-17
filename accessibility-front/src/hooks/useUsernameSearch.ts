'use client';
import { useUser } from '@/providers/User';
import { useState } from 'react';
import useSWR from 'swr';

// Existing usernames starting with what is typed (GET /api/users/search/), as Select
// options, so people pick an account instead of retyping a NetID.
export function useUsernameSearch() {
    const { handlerUserApiRequest } = useUser();
    const [query, setQuery] = useState('');
    const { data } = useSWR(
        `/api/users/search/?q=${encodeURIComponent(query.trim())}`,
        handlerUserApiRequest<string[]>,
        { keepPreviousData: true }
    );
    return {
        options: (data ?? []).map((name) => ({ value: name, label: name })),
        onSearch: setQuery,
    };
}
