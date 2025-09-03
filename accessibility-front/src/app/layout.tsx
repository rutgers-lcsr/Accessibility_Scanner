import { rutgersTheme } from '@/lib/theme';
import { User } from '@/lib/types/user';
import { AlertsProvider } from '@/providers/Alerts';
import { AntdRegistry } from '@ant-design/nextjs-registry';
import '@ant-design/v5-patch-for-react-19';
import { ConfigProvider, Layout } from 'antd';
import 'antd/dist/reset.css';
import type { Metadata } from 'next';
import { getCurrentUser, isLoggedIn } from 'next-cas-client/app';
import { Geist, Geist_Mono } from 'next/font/google';
import { headers } from 'next/headers';
import { redirect } from 'next/navigation';
import TabNav from '../components/TabNav';
import { UserProvider } from '../providers/User';
import './globals.css';

const geistSans = Geist({
    variable: '--font-geist-sans',
    subsets: ['latin'],
});

const geistMono = Geist_Mono({
    variable: '--font-geist-mono',
    subsets: ['latin'],
});

export const metadata: Metadata = {
    title: 'A11y',
    description: 'LCSR Accessibility Audit Tool',
    icons: {
        icon: '/favicon.ico',
        apple: '/apple-touch-icon.png',
    },
};

const base_url = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';

export default async function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    const user: User | null = await getCurrentUser();
    const headersList = await headers()

    // If we are in development allow access to all routes
    if (!user || !await isLoggedIn()) {
        if(process.env.NODE_ENV == "production"){

            // this prevents infinite redirect loops, its a workaround because once a user is redirected the referer header is set and next time it will not redirect
            // its dumb but it works
            if (headersList.get("Referer") != base_url + "/login") {
                // If the user is not logged in, redirect to the login page
                redirect('/login')
            }

        }
    }


    return (
        <html lang="en">
            <body className={`${geistSans.variable} ${geistMono.variable}`}>
                <AntdRegistry>
                    <Layout hasSider>
                        <ConfigProvider theme={rutgersTheme}>
                            <AlertsProvider>
                                <UserProvider user={user}>
                                    <TabNav user={user} />
                                    <Layout>{children}</Layout>
                                </UserProvider>
                            </AlertsProvider>
                        </ConfigProvider>
                    </Layout>
                </AntdRegistry>
            </body>
        </html>
    );
}
