'use client';
/**
 * Tab Navigation Component
 * Handles the navigation between different tabs in the application.
 */

import { User } from '@/lib/types/user';
import {
    CloudOutlined,
    CloudServerOutlined,
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

export default function TabNav({ user }: Props) {
    const router = useRouter();
    const [collapsed, setCollapsed] = useState(true);
    const pathname = usePathname();

    const tabRoutes: { [key: string]: string } = {
        '1': '/',
        '2': '/websites',
        '3': '/reports',
        '5': user && user.is_admin ? '/domains' : '/login',
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

    const items: ItemType<MenuItemType>[] = user && user.is_admin 
        ? [
              { label: 'Home', key: '1', icon: <HomeOutlined /> },
              { label: 'Domains', key: '5', icon: <CloudOutlined /> },
              { label: 'Websites', key: '2', icon: <CloudServerOutlined /> },
              { label: 'Reports', key: '3', icon: <SolutionOutlined /> },
              
          ]
        : [
              { label: 'Home', key: '1', icon: <HomeOutlined /> },
              { label: 'Websites', key: '2', icon: <CloudServerOutlined /> },
              { label: 'Reports', key: '3', icon: <SolutionOutlined /> },
          ];

    if (user){ 
        items.push({
                  label: 'Logout',
                  key: '6',
                  icon: <LogoutOutlined />,
                  onClick: () => {
                      logout();
                  },
              });
    }else {
        items.push({
            label: 'Login',
            key: '5',
            icon: <LoginOutlined />,
            onClick: () => {
                login()
            }
        });
    }


    return (
        <Sider
            style={{
                position: 'sticky',
            }}
            role="navigation"
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
