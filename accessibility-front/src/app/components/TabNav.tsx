"use client";

import { Space, Tabs } from "antd";
import { useRouter } from "next/navigation";
import { usePathname } from 'next/navigation';
export default function TabNav() {
    const router = useRouter();
    const pathname = usePathname();

    const tabRoutes: { [key: string]: string } = {
        "1": "/",
        "2": "/websites",
        "3": "/settings",
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

    return (
        <Space direction="vertical" style={{ width: "100%", height: "100vh" }}>
            <Tabs
                activeKey={activeKey()}
                tabPosition="left"
                items={[
                    { label: "Home", key: "1" },
                    { label: "Websites", key: "2" },
                    { label: "Settings", key: "3" },
                ]}
                style={{ height: "100%" }}
                onChange={(key) => router.push(tabRoutes[key])}
            />
            <div className="h-lvh w-full">

            </div>
        </Space>
    );
}
