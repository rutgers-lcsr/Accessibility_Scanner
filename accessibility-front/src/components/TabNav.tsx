'use client';
/**
 * Tab Navigation Component
 * Handles the navigation between different tabs in the application.
 */

import { User } from '@/lib/types/user';
import {
    CloudOutlined,
    CloudServerOutlined,
    FormOutlined,
    HomeOutlined,
    LoginOutlined,
    LogoutOutlined,
    SolutionOutlined,
} from '@ant-design/icons';
import { Menu } from 'antd';
import Sider from 'antd/es/layout/Sider';
import { ItemType, MenuItemType } from 'antd/es/menu/interface';
import { login, logout } from 'next-cas-client';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';

type Props = {
    user: User | null;
};

type TabRoute = {
    key: string;
    path: string;
};

export default function TabNav({ user }: Props) {
    const router = useRouter();
    const [collapsed, setCollapsed] = useState(true);
    const pathname = usePathname();

    // Define tab routes
    const tabRoutes: TabRoute[] = [
        { key: '1', path: '/' },
        { key: '2', path: '/websites' },
        { key: '3', path: '/reports' },
        { key: '4', path: '/rules' },
        { key: '5', path: user && user.is_admin ? '/domains' : '/login' },
        { key: '6', path: '/login' },
    ];

    // Find the active tab key based on current pathname
    const activeKey = tabRoutes.reduce((acc, route) => {
        if (pathname.startsWith(route.path) && route.path.length > acc.length) {
            return route.key;
        }
        return acc;
    }, '1');

    // Build menu items
    const items: ItemType<MenuItemType>[] =
        user && user.is_admin
            ? [
                  { label: 'Home', key: '1', icon: <HomeOutlined /> },
                  { label: 'Domains', key: '5', icon: <CloudOutlined /> },
                  { label: 'Rules', key: '4', icon: <FormOutlined /> },
                  { label: 'Websites', key: '2', icon: <CloudServerOutlined /> },
                  { label: 'Reports', key: '3', icon: <SolutionOutlined /> },
              ]
            : [
                  { label: 'Home', key: '1', icon: <HomeOutlined /> },
                  { label: 'Websites', key: '2', icon: <CloudServerOutlined /> },
                  { label: 'Reports', key: '3', icon: <SolutionOutlined /> },
              ];

    // Add login/logout item
    items.push(
        user
            ? {
                  label: 'Logout',
                  key: '6',
                  icon: <LogoutOutlined />,
                  onClick: () => logout(),
              }
            : {
                  label: 'Login',
                  key: '5',
                  icon: <LoginOutlined />,
                  onClick: () => login(),
              }
    );

    // Handle tab selection
    const handleSelect = (info: { key: string }) => {
        const route = tabRoutes.find((r) => r.key === info.key)?.path;
        if (route) {
            router.push(route);
        }
    };

    return (
        <Sider
            style={{ position: 'sticky' }}
            role="navigation"
            className="scrollbar-thin scrollbar-gutter sticky top-0 bottom-0 h-[100vh] overflow-auto"
            theme="light"
            collapsible
            aria-label="Tab Navigation"
            collapsed={collapsed}
            onCollapse={setCollapsed}
        >
            <div className="p-4 pl-3 text-xl font-bold">A11y</div>
            <Menu onClick={handleSelect} selectedKeys={[activeKey]} mode="inline" items={items} />
        </Sider>
    );
}
