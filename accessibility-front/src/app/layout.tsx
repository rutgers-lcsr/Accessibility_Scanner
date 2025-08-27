import '@ant-design/v5-patch-for-react-19';
import 'antd/dist/reset.css';
import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

import { rutgersTheme } from '@/lib/theme';
import { getUser } from '@/lib/user';
import { AlertsProvider } from '@/providers/Alerts';
import { AntdRegistry } from '@ant-design/nextjs-registry';
import { ConfigProvider, Layout } from 'antd';
import TabNav from '../components/TabNav';
import { UserProvider } from '../providers/User';
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

export default async function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    const user = await getUser();

    return (
        <html lang="en">
            <body className={`${geistSans.variable} ${geistMono.variable}`}>
                <AntdRegistry>
                    <Layout hasSider>
                        <ConfigProvider theme={rutgersTheme}>
                            <AlertsProvider>
                                <UserProvider>
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
