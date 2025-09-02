import { User } from '@/lib/types/user';
import { ReportsProvider } from '@/providers/Reports';
import { Header } from 'antd/es/layout/layout';
import { getCurrentUser } from 'next-cas-client/app';
import { ReactNode } from 'react';

export default  async function Layout({ children }: { children: ReactNode }) {

    const user = await getCurrentUser<User>();

    return (
        <>
            <ReportsProvider user={user}>
                <Header></Header>
                <div className="p-4" role="main">
                    {children}
                </div>
            </ReportsProvider>
        </>
    );
}
