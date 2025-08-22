"use client";

import { Menu, Space, Tabs } from "antd";
import { useRouter } from "next/navigation";
import { usePathname } from 'next/navigation';
import { useUser } from "../providers/User";
import Sider from "antd/es/layout/Sider";
import { useState } from "react";
import { HomeOutlined, CloudServerOutlined, SolutionOutlined, ProfileOutlined, LoginOutlined } from '@ant-design/icons'

export default function TabNav() {
    const router = useRouter();
    const [collapsed, setCollapsed] = useState(false);
    const { user } = useUser();
    const pathname = usePathname();

    const tabRoutes: { [key: string]: string } = {
        "1": "/",
        "2": "/websites",
        "3": "/reports",
        "5": user ? "/dashboard" : "/login",
    };
    const activeKey = () => {

        const currentPath = pathname;
        for (const key in tabRoutes) {
            if (currentPath === tabRoutes[key]) {
                return key;
            }
        }
        return "1"; // Default to Home if no match found

    }

    const items = user ? [
        { label: "Home", key: "1", icon: <HomeOutlined /> },
        { label: "Websites", key: "2", icon: <CloudServerOutlined /> },
        { label: "Reports", key: "3", icon: <SolutionOutlined /> },
        { label: "Dashboard", key: "5", icon: <ProfileOutlined /> },
    ] : [
        { label: "Home", key: "1", icon: <HomeOutlined /> },
        { label: "Websites", key: "2", icon: <CloudServerOutlined /> },
        { label: "Reports", key: "3", icon: <SolutionOutlined /> },
        { label: "Login", key: "5", icon: <LoginOutlined /> },
    ];

    return (
        <Sider style={{
            position: 'sticky',
        }} className="overflow-auto h-[100vh] sticky top-0 bottom-0 scrollbar-thin scrollbar-gutter" theme="light" collapsible collapsed={collapsed} onCollapse={(value) => setCollapsed(value)}>
            <div className="p-6">Access</div>
            <Menu onSelect={(info) => router.push(tabRoutes[info.key])} defaultSelectedKeys={[activeKey()]} mode="inline" items={items} />
        </Sider>



    );
}
