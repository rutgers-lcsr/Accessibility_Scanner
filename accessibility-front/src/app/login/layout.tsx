import { DomainProvider } from '@/providers/Domain';
import { ReportsProvider } from '@/providers/Reports';
import { UserProvider } from '@/providers/User';
import { Header } from 'antd/es/layout/layout';
import { ReactNode } from 'react';

export default function Layout({ children }: { children: ReactNode }) {
    return (
        <>
            <Header></Header>
            <div className="p-4" role="main">
                {children}
            </div>
        </>
    );
}
