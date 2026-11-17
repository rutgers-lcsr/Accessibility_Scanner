'use client';
/**
 * Main navigation. From the md breakpoint up it is a collapsible sidebar (labels shown by
 * default, the choice remembered in a cookie); below it, a top bar opens the same links in a
 * drawer. Items are real links, so they can be opened in a new tab.
 */

import { NAV_COLLAPSED_COOKIE } from '@/lib/nav';
import { PublicUser } from '@/lib/types/user';
import {
    BarChartOutlined,
    CloudOutlined,
    CloudServerOutlined,
    DashboardOutlined,
    FormOutlined,
    HomeOutlined,
    LoginOutlined,
    LogoutOutlined,
    MenuFoldOutlined,
    MenuOutlined,
    MenuUnfoldOutlined,
    QuestionCircleOutlined,
    SettingOutlined,
    SolutionOutlined,
    TeamOutlined,
    ThunderboltOutlined,
} from '@ant-design/icons';
import { Button, Drawer, Layout } from 'antd';
import { login, logout } from 'next-cas-client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ReactNode, useState } from 'react';

type NavLink = { path: string; label: string; icon: ReactNode };

const MAIN: NavLink[] = [
    { path: '/', label: 'Home', icon: <HomeOutlined /> },
    { path: '/dashboard', label: 'Dashboard', icon: <DashboardOutlined /> },
    { path: '/websites', label: 'Websites', icon: <CloudServerOutlined /> },
    { path: '/scan', label: 'Quick scan', icon: <ThunderboltOutlined /> },
    { path: '/reports', label: 'Reports', icon: <SolutionOutlined /> },
    { path: '/scorecards', label: 'Scorecards', icon: <BarChartOutlined /> },
];

const ADMIN: NavLink[] = [
    { path: '/owners', label: 'Owners', icon: <TeamOutlined /> },
    { path: '/domains', label: 'Domains', icon: <CloudOutlined /> },
    { path: '/rules', label: 'Rules', icon: <FormOutlined /> },
];

const SUPPORT: NavLink[] = [
    { path: '/settings', label: 'Settings', icon: <SettingOutlined /> },
    { path: '/help', label: 'Help', icon: <QuestionCircleOutlined /> },
];

const ALL_PATHS = [...MAIN, ...ADMIN, ...SUPPORT].map((l) => l.path);

/** The nav path the current page belongs to: the longest one that prefixes it. */
function activePath(pathname: string): string {
    const matches = ALL_PATHS.filter((p) =>
        p === '/' ? pathname === '/' : pathname === p || pathname.startsWith(`${p}/`)
    );
    return matches.sort((a, b) => b.length - a.length)[0] ?? '';
}

// The navigation as plain links in lists. antd's Menu wrapped each link in role=menuitem
// inside a focusable role=menu (a stray Tab stop, links announced as menu items with their
// icon name first) and made sign-out a list item no Tab reached.
function NavList({
    user,
    collapsed,
    pathname,
    onNavigate,
}: {
    user: PublicUser | null;
    collapsed: boolean;
    pathname: string;
    onNavigate?: () => void;
}) {
    const current = activePath(pathname);
    const row = `flex h-10 w-full items-center gap-3 rounded-lg text-sm transition-colors ${collapsed ? 'justify-center px-0' : 'px-4'}`;
    const link = (item: NavLink) => {
        const active = item.path === current;
        return (
            <li key={item.path}>
                <Link
                    href={item.path}
                    aria-current={active ? 'page' : undefined}
                    title={collapsed ? item.label : undefined}
                    onClick={onNavigate}
                    className={`${row} ${active ? 'font-medium' : 'hover:bg-[#f3f3f3]'}`}
                    // Inline: antd's unlayered link styles (colour, transparent background)
                    // beat Tailwind classes on <a>.
                    style={{
                        textDecoration: 'none',
                        color: active ? '#b3002d' : '#222222',
                        background: active ? '#fdecef' : undefined,
                    }}
                >
                    <span aria-hidden="true" className="text-base leading-none">
                        {item.icon}
                    </span>
                    <span className={collapsed ? 'sr-only' : ''}>{item.label}</span>
                </Link>
            </li>
        );
    };
    const list = (items: NavLink[], label?: string) => (
        <ul aria-label={label} className="m-0 flex list-none flex-col gap-1 p-0 px-1">
            {items.map(link)}
        </ul>
    );
    return (
        <div className="flex flex-col gap-1 py-1">
            {list(MAIN)}
            {user?.is_admin && (
                <>
                    {collapsed ? (
                        <hr className="mx-3 my-2 border-[#efefef]" />
                    ) : (
                        <p className="px-5 pt-3 pb-1 text-xs text-[#595959]" style={{ margin: 0 }}>
                            Admin
                        </p>
                    )}
                    {list(ADMIN, 'Admin')}
                </>
            )}
            <hr className="mx-3 my-2 border-[#efefef]" />
            {list(SUPPORT)}
            <div className="px-1">
                <button
                    type="button"
                    // Who is signed in, so a dev sign-in or a shared machine is never a guess.
                    title={user ? `Signed in as ${user.email}` : undefined}
                    aria-label={
                        collapsed ? (user ? `Log out ${user.username}` : 'Log in') : undefined
                    }
                    onClick={() => (user ? logout() : login())}
                    className={`${row} cursor-pointer border-0 bg-transparent text-[#222222] hover:bg-[#f3f3f3]`}
                >
                    <span aria-hidden="true" className="text-base leading-none">
                        {user ? <LogoutOutlined /> : <LoginOutlined />}
                    </span>
                    <span className={collapsed ? 'sr-only' : ''}>
                        {user ? `Logout (${user.username})` : 'Login'}
                    </span>
                </button>
            </div>
        </div>
    );
}

type Props = {
    user: PublicUser | null;
    defaultCollapsed?: boolean;
};

export default function TabNav({ user, defaultCollapsed = false }: Props) {
    const pathname = usePathname();
    const [collapsed, setCollapsed] = useState(defaultCollapsed);

    const onCollapse = (value: boolean) => {
        setCollapsed(value);
        document.cookie = `${NAV_COLLAPSED_COOKIE}=${value ? '1' : '0'}; path=/; max-age=31536000; samesite=lax`;
    };

    return (
        // The column, not the sticky sider, carries the background and edge, so the sidebar
        // reads as one panel down the whole page (the sider itself is only 100vh tall).
        <div className="hidden shrink-0 border-r border-[#e4e4e4] bg-white md:block print:hidden">
            <Layout.Sider
                theme="light"
                width={208}
                collapsible
                collapsed={collapsed}
                // antd's own trigger is a div that keyboard users cannot reach; ours is a button.
                trigger={null}
                style={{
                    position: 'sticky',
                    top: 0,
                    height: '100vh',
                }}
            >
                <div className="flex h-full flex-col">
                    <Link
                        href="/"
                        aria-label="A11y home"
                        style={{ color: '#111111' }}
                        className={`block py-5 text-2xl font-bold tracking-tight ${collapsed ? 'text-center' : 'px-6'}`}
                    >
                        A11y
                    </Link>
                    <nav aria-label="Main" className="min-h-0 flex-1 overflow-y-auto">
                        <NavList user={user} collapsed={collapsed} pathname={pathname} />
                    </nav>
                    <div className="border-t border-[#efefef] p-2">
                        <Button
                            type="text"
                            block
                            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                            aria-label={collapsed ? 'Expand navigation' : 'Collapse navigation'}
                            aria-expanded={!collapsed}
                            onClick={() => onCollapse(!collapsed)}
                            style={{ justifyContent: collapsed ? 'center' : 'flex-start' }}
                        >
                            {collapsed ? null : 'Collapse'}
                        </Button>
                    </div>
                </div>
            </Layout.Sider>
        </div>
    );
}

/** Top bar with a menu button, shown below the md breakpoint instead of the sidebar. */
export function MobileNav({ user }: { user: PublicUser | null }) {
    const pathname = usePathname();
    const [open, setOpen] = useState(false);

    return (
        <div className="sticky top-0 z-20 flex items-center gap-1 border-b border-gray-200 bg-white px-2 py-2 md:hidden print:hidden">
            <Button
                type="text"
                size="large"
                icon={<MenuOutlined />}
                aria-label="Open navigation"
                aria-haspopup="dialog"
                aria-expanded={open}
                onClick={() => setOpen(true)}
            />
            <Link
                href="/"
                aria-label="A11y home"
                style={{ color: '#111111' }}
                className="text-xl font-bold tracking-tight"
            >
                A11y
            </Link>
            <Drawer
                title="A11y"
                placement="left"
                size={264}
                open={open}
                onClose={() => setOpen(false)}
                styles={{ body: { padding: 0 } }}
            >
                <nav aria-label="Main">
                    <NavList
                        user={user}
                        collapsed={false}
                        pathname={pathname}
                        onNavigate={() => setOpen(false)}
                    />
                </nav>
            </Drawer>
        </div>
    );
}
