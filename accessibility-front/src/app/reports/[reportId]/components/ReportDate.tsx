'use client';

import { useSyncExternalStore } from 'react';

interface ReportDateProps {
    dateString: string;
}

const noSubscription = () => () => {};

const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    if (isNaN(date.getTime())) return 'N/A';
    return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
};

// The report's time in the reader's time zone. Formatted in the browser only: the server
// runs in UTC, so its text would not match the browser's and hydration would fail.
function ReportDate({ dateString }: ReportDateProps) {
    const formatted = useSyncExternalStore(
        noSubscription,
        () => formatDate(dateString),
        () => null
    );
    return <span>Report date: {formatted}</span>;
}

export default ReportDate;
