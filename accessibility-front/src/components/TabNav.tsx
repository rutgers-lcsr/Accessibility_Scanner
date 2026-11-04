'use client';
/**
 * Main navigation. From the md breakpoint up it is a collapsible sidebar (labels shown by
 * default, the choice remembered in a cookie); below it, a top bar opens the same links in a
 * drawer. Items are real links, so they can be opened in a new tab.
 */

import { NAV_COLLAPSED_COOKIE } from '@/lib/nav';
import { PublicUser } from '@/lib/types/user';
import {
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
import { Button, Drawer, Layout, Menu, type MenuProps } from 'antd';
import { login, logout } from 'next-cas-client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ReactNode, useState } from 'react';

type MenuItem = NonNullable<MenuProps['items']>[number];
type NavLink = { path: string; label: string; icon: ReactNode };

const MAIN: NavLink[] = [
    { path: '/', label: 'Home', icon: <HomeOutlined /> },
    { path: '/dashboard', label: 'Dashboard', icon: <DashboardOutlined /> },
    { path: '/websites', label: 'Websites', icon: <CloudServerOutlined /> },
    { path: '/scan', label: 'Quick scan', icon: <ThunderboltOutlined /> },
    { path: '/reports', label: 'Reports', icon: <SolutionOutlined /> },
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

function toItem(link: NavLink): MenuItem {
    return { key: link.path, icon: link.icon, label: <Link href={link.path}>{link.label}</Link> };
}

function navItems(user: PublicUser | null, collapsed: boolean): MenuItem[] {
    const items: MenuItem[] = MAIN.map(toItem);
    if (user?.is_admin) {
        // Collapsed there is no room for a group title, so a rule separates the admin pages.
        items.push(
            collapsed
                ? { type: 'divider' }
                : { type: 'group', key: 'admin', label: 'Admin', children: ADMIN.map(toItem) }
        );
        if (collapsed) items.push(...ADMIN.map(toItem));
    }
    items.push({ type: 'divider' }, ...SUPPORT.map(toItem));
    items.push(
        user
            ? {
                  // Who is signed in, so a dev sign-in or a shared machine is never a guess.
                  label: `Logout (${user.username})`,
                  title: `Signed in as ${user.email}`,
                  key: 'logout',
                  icon: <LogoutOutlined />,
                  onClick: () => logout(),
              }
            : { label: 'Login', key: 'login', icon: <LoginOutlined />, onClick: () => login() }
    );
    return items;
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
        <div className="hidden shrink-0 border-r border-[#e4e4e4] bg-white md:block">
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
                        <Menu
                            mode="inline"
                            selectedKeys={[activePath(pathname)]}
                            items={navItems(user, collapsed)}
                            style={{ borderInlineEnd: 0 }}
                        />
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
        <div className="sticky top-0 z-20 flex items-center gap-1 border-b border-gray-200 bg-white px-2 py-2 md:hidden">
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
                    <Menu
                        mode="inline"
                        selectedKeys={[activePath(pathname)]}
                        items={navItems(user, false)}
                        onClick={() => setOpen(false)}
                        style={{ borderInlineEnd: 0 }}
                    />
                </nav>
            </Drawer>
        </div>
    );
}
