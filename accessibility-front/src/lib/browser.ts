'use client';
function getInitalPageSize(): PageSize {
    if (typeof window === 'undefined' || !window.localStorage) {
        return 5;
    }
    const saved = localStorage.getItem('websitePageSize');
    if (saved) {
        const parsed = parseInt(saved, 10);
        if (!isNaN(parsed) && parsed > 0) {
            if (pageSizeOptions.map(Number).includes(parsed)) {
                return parsed as PageSize;
            }
            return 5; // Default to 5 if not one of the expected values
        }
    }

    if (typeof window !== 'undefined') {
        const width = window.innerWidth;
        if (width < 600) return 5;
        if (width < 900) return 10;
        return 20;
    }
    return 5;
}

const pageSizeOptions = ['5', '10', '20', '50', '100'];
export type PageSize = 5 | 10 | 20 | 50 | 100;

export { getInitalPageSize, pageSizeOptions };
