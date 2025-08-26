'use client';
/**
 * Tab Navigation Component
 * Handles the navigation between different tabs in the application.
 */

import { Menu } from 'antd';
import { useRouter } from 'next/navigation';
import { usePathname } from 'next/navigation';
import { useUser } from '../providers/User';
import Sider from 'antd/es/layout/Sider';
import { useState } from 'react';
import {
    HomeOutlined,
    CloudServerOutlined,
    SolutionOutlined,
    LoginOutlined,
    CloudOutlined,
} from '@ant-design/icons';

export default function TabNav() {
    const router = useRouter();
    const [collapsed, setCollapsed] = useState(true);
    const { user, logout, is_admin } = useUser();
    const pathname = usePathname();

    const tabRoutes: { [key: string]: string } = {
        '1': '/',
        '2': '/websites',
        '3': '/reports',
        '5': user && is_admin ? '/domains' : '/login',
        '6': '/login',
    };
    // Find the longest matching route key for the current pathname
    const activeKey = (() => {
        let longestMatch = '1';
        let maxLength = 0;
        for (const key in tabRoutes) {
            const route = tabRoutes[key];
            if (pathname.startsWith(route) && route.length > maxLength) {
                longestMatch = key;
                maxLength = route.length;
            }
        }
        return longestMatch;
    })();

    const items = user
        ? [
              { label: 'Home', key: '1', icon: <HomeOutlined /> },
              { label: 'Domains', key: '5', icon: <CloudOutlined /> },
              { label: 'Websites', key: '2', icon: <CloudServerOutlined /> },
              { label: 'Reports', key: '3', icon: <SolutionOutlined /> },
              {
                  label: 'Logout',
                  key: '6',
                  icon: <LoginOutlined />,
                  onClick: () => {
                      logout().then(() => router.push('/login'));
                  },
              },
          ]
        : [
              { label: 'Home', key: '1', icon: <HomeOutlined /> },
              { label: 'Websites', key: '2', icon: <CloudServerOutlined /> },
              { label: 'Reports', key: '3', icon: <SolutionOutlined /> },
              { label: 'Login', key: '5', icon: <LoginOutlined /> },
          ];

    return (
        <Sider
            style={{
                position: 'sticky',
            }}
            className="scrollbar-thin scrollbar-gutter sticky top-0 bottom-0 h-[100vh] overflow-auto"
            theme="light"
            collapsible
            collapsed={collapsed}
            onCollapse={(value) => setCollapsed(value)}
        >
            <div className="p-4 pl-2 text-xl font-bold">A11y</div>
            <Menu
                onSelect={(info) => {
                    const route = tabRoutes[info.key] + '?';

                    router.push(route, undefined);
                }}
                selectedKeys={[activeKey]}
                mode="inline"
                items={items}
            />
        </Sider>
    );
}
