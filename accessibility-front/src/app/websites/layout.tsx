import { User } from '@/lib/types/user';
import { WebsitesProvider } from '@/providers/Websites';
import { Header } from 'antd/es/layout/layout';
import { getCurrentUser } from 'next-cas-client/app';
import { ReactNode } from 'react';

export default async function Layout({ children }: { children: ReactNode }) {

    const user = await getCurrentUser<User>(); // Assume this function fetches the current user

    return (
        <WebsitesProvider user={user}>
            <Header></Header>
            <div className="p-4" role="main">
                {children}
            </div>
        </WebsitesProvider>
    );
}
