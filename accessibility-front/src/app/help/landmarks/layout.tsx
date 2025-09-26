import { ReactNode } from 'react';

export default async function Layout({ children }: { children: ReactNode }) {
    return (
        <>
            <div className="p-4">{children}</div>
        </>
    );
}
