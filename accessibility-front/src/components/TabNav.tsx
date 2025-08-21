"use client";

import { Space, Tabs } from "antd";
import { useRouter } from "next/navigation";
import { usePathname } from 'next/navigation';
import { useUser } from "../providers/User";
export default function TabNav() {
    const router = useRouter();
    const { user } = useUser();
    const pathname = usePathname();

    const tabRoutes: { [key: string]: string } = {
        "1": "/",
        "2": "/websites",
        "3": "/reports",
        "4": "/settings",
        "5": "/profile",
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
        { label: "Home", key: "1" },
        { label: "Websites", key: "2" },
        { label: "Reports", key: "3" },
        { label: "Settings", key: "4" },
        { label: "Profile", key: "5" },
    ] : [
        { label: "Home", key: "1" },
        { label: "Websites", key: "2" },
        { label: "Reports", key: "3" },
        { label: "Settings", key: "4" },
        { label: "Login", key: "5" },
    ];

    return (
        <Space direction="vertical" style={{}}>
            <div className="h-svh" role="navigation" aria-label="Navigation">
                <Tabs
                    activeKey={activeKey()}
                    tabPosition="left"
                    items={items}
                    style={{ height: "100%" }}
                    onChange={(key) => router.push(tabRoutes[key], {
                        'scroll': true,
                    })}
                    className="h-lvh w-full"

                >
                </Tabs>
                {user && <div className="text-center">Welcome, {user.email}!</div>}
            </div>

        </Space>
    );
}
