import { SettingsProvider } from '@/providers/Settings';
import { Header } from 'antd/es/layout/layout';
import { ReactNode } from 'react';

export default async function Layout({ children }: { children: ReactNode }) {
    return (
        <SettingsProvider>
            <Header></Header>
            <div className="p-4" role="main">
                {children}
            </div>
        </SettingsProvider>
    );
}
