import { ReactNode } from 'react';

// Building blocks shared by the website settings panels (AdminItems, WebsiteAdminItems).

// A labelled control with an optional one-line note under it.
export function Field({
    id,
    label,
    help,
    children,
}: {
    id: string;
    label: string;
    help?: ReactNode;
    children: ReactNode;
}) {
    return (
        <div>
            <label htmlFor={id} className="mb-1 block text-sm font-medium text-gray-700">
                {label}
            </label>
            {children}
            {help && <div className="mt-1 text-xs text-gray-500">{help}</div>}
        </div>
    );
}

// antd's reset.css sizes <legend> at 1.5em and that unlayered rule beats Tailwind's
// utilities, so the two properties it sets are given inline.
export function Legend({ children }: { children: ReactNode }) {
    return (
        <legend
            className="font-semibold tracking-wide text-gray-600 uppercase"
            style={{ fontSize: '0.75rem', marginBottom: 8 }}
        >
            {children}
        </legend>
    );
}
