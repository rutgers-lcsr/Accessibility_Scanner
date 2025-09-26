import { rutgersTheme } from '@/lib/theme';
import { User } from '@/lib/types/user';
import { AlertsProvider } from '@/providers/Alerts';
import { AntdRegistry } from '@ant-design/nextjs-registry';
import '@ant-design/v5-patch-for-react-19';
import { ConfigProvider, Layout } from 'antd';
import 'antd/dist/reset.css';
import { Footer } from 'antd/es/layout/layout';
import type { Metadata } from 'next';
import { getCurrentUser } from 'next-cas-client/app';
import { Geist, Geist_Mono } from 'next/font/google';
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

export default async function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    const user: User | null = await getCurrentUser();

    return (
        <html lang="en" className="scroll-smooth h-full">
            <body className={`${geistSans.variable} ${geistMono.variable}`}>
                <AntdRegistry>
                    <Layout hasSider>
                        <ConfigProvider theme={rutgersTheme}>
                            <AlertsProvider>
                                <UserProvider user={user}>
                                    <TabNav user={user} />
                                    <Layout>
                                        <div style={{ minHeight: '100vh' }}>{children}</div>
                                        <Footer
                                            style={{
                                                textAlign: 'center',
                                                position: 'relative',
                                                marginTop: 20,
                                                fontSize: '0.9rem',
                                                backgroundColor: 'rgba(251, 255, 255, 1)',
                                            }}
                                        >
                                            <br />
                                            For technical assistance, feel free to contact the LCSR
                                            at{' '}
                                            <a
                                                className="font-bold hover:underline"
                                                href="mailto:a11y@cs.rutgers.edu"
                                            >
                                                a11y@cs.rutgers.edu
                                            </a>
                                            . We are here to help you improve the accessibility of
                                            your website and ensure compliance with accessibility
                                            standards.
                                            <br />
                                            &copy; {new Date().getFullYear()} LCSR CS Department
                                            Rutgers University -{' '}
                                            <a
                                                href="https://accessibility.rutgers.edu/"
                                                className="font-bold hover:underline"
                                            >
                                                University Accessibility
                                            </a>
                                        </Footer>
                                    </Layout>
                                </UserProvider>
                            </AlertsProvider>
                        </ConfigProvider>
                    </Layout>
                </AntdRegistry>
            </body>
        </html>
    );
}
