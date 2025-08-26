'use client'; // Error boundaries must be Client Components

import PageError from '@/components/PageError';
import { Header } from 'antd/es/layout/layout';
import { useEffect } from 'react';

export default function Error({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        // Log the error to an error reporting service
        console.error(error);
    }, [error]);

    return (
        <div>
            <Header />
            <PageError status={500} />
        </div>
    );
}
