import { WebsitesProvider } from '@/providers/Websites';
import { Header } from 'antd/es/layout/layout';
import { ReactNode } from 'react';

export default function Layout({ children }: { children: ReactNode }) {
    return (
        <WebsitesProvider>
            <Header></Header>
            <div className="p-4" role="main">
                {children}
            </div>
        </WebsitesProvider>
    );
}
