'use client';

import React from 'react';

interface ReportDateProps {
    dateString: string;
}

const ReportDate: React.FC<ReportDateProps> = ({ dateString }) => {
    const date = new Date(dateString);
    const formattedDate = date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'numeric',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });
    if (isNaN(date.getTime())) {
        return <h3 className="mb-2 text-lg text-gray-500">Report Date: N/A</h3>;
    }
    return <h3 className="mb-2 text-lg text-gray-500">Report Date: {formattedDate}</h3>;
};

export default ReportDate;
