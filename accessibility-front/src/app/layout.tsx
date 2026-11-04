import { rutgersTheme } from '@/lib/theme';
import { NAV_COLLAPSED_COOKIE } from '@/lib/nav';
import { User, toPublicUser } from '@/lib/types/user';
import { AlertsProvider } from '@/providers/Alerts';
import { AntdRegistry } from '@ant-design/nextjs-registry';
import { ConfigProvider, Layout } from 'antd';
import 'antd/dist/reset.css';
import { Footer } from 'antd/es/layout/layout';
import type { Metadata } from 'next';
import { getCurrentUser } from 'next-cas-client/app';
import { Geist, Geist_Mono } from 'next/font/google';
import { cookies } from 'next/headers';
import Link from 'next/link';
import TabNav, { MobileNav } from '../components/TabNav';
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

const footerLink = 'font-medium text-[#007fac] underline underline-offset-2 hover:text-[#005f80]';

export default async function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    const user = toPublicUser(await getCurrentUser<User>());
    const navCollapsed = (await cookies()).get(NAV_COLLAPSED_COOKIE)?.value === '1';

    return (
        <html lang="en" className="scroll-smooth h-full">
            <body className={`${geistSans.variable} ${geistMono.variable}`}>
                <a
                    href="#main-content"
                    className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[2000] focus:rounded-md focus:bg-white focus:px-4 focus:py-2 focus:font-medium focus:text-gray-900 focus:shadow-lg focus:outline-2 focus:outline-[#cc0033]"
                >
                    Skip to main content
                </a>
                <AntdRegistry>
                    <ConfigProvider theme={rutgersTheme}>
                        <Layout hasSider>
                            <AlertsProvider>
                                <UserProvider user={user}>
                                    <TabNav user={user} defaultCollapsed={navCollapsed} />
                                    <Layout style={{ minWidth: 0 }}>
                                        <MobileNav user={user} />
                                        <main
                                            id="main-content"
                                            tabIndex={-1}
                                            style={{ minHeight: '100vh', outline: 'none' }}
                                        >
                                            {children}
                                        </main>
                                        <Footer
                                            style={{
                                                padding: '24px 24px 28px',
                                                marginTop: 20,
                                                borderTop: '1px solid #e4e4e4',
                                            }}
                                        >
                                            <div className="max-w-4xl space-y-2 text-sm leading-relaxed text-gray-600">
                                                <p style={{ margin: 0 }}>
                                                    Rutgers is an equal access/equal opportunity
                                                    institution. Individuals with disabilities are
                                                    encouraged to direct suggestions, comments, or
                                                    complaints concerning any accessibility issues
                                                    with Rutgers web sites to:{' '}
                                                    <Link
                                                        className={footerLink}
                                                        href="mailto:accessibility@rutgers.edu"
                                                    >
                                                        accessibility@rutgers.edu
                                                    </Link>{' '}
                                                    or complete the{' '}
                                                    <Link
                                                        className={footerLink}
                                                        href="https://it.rutgers.edu/it-accessibility-initiative/barrierform/"
                                                    >
                                                        Report Accessibility Barrier or Provide
                                                        Feedback Form
                                                    </Link>
                                                    .
                                                </p>
                                                <p style={{ margin: 0 }}>
                                                    For technical assistance, feel free to contact
                                                    the LCSR at{' '}
                                                    <Link
                                                        className={footerLink}
                                                        href="mailto:a11y@cs.rutgers.edu"
                                                    >
                                                        a11y@cs.rutgers.edu
                                                    </Link>
                                                    . We are here to help you improve the
                                                    accessibility of your website and ensure
                                                    compliance with accessibility standards.
                                                </p>
                                                <p style={{ margin: 0 }} className="text-gray-500">
                                                    &copy; {new Date().getFullYear()} LCSR CS
                                                    Department Rutgers University -{' '}
                                                    <Link
                                                        href="https://accessibility.rutgers.edu/"
                                                        className={footerLink}
                                                    >
                                                        University Accessibility
                                                    </Link>
                                                </p>
                                            </div>
                                        </Footer>
                                    </Layout>
                                </UserProvider>
                            </AlertsProvider>
                        </Layout>
                    </ConfigProvider>
                </AntdRegistry>
            </body>
        </html>
    );
}
