import { ReportsProvider } from "@/providers/Reports";
import { Header } from "antd/es/layout/layout";
import { ReactNode } from "react";

export default function Layout({ children }: { children: ReactNode }) {
    return (
        <>
            <ReportsProvider>
                <Header>
                    <h1>Reports</h1>
                </Header>
                <div className="p-4" role="main">{children}</div>
            </ReportsProvider>
        </>
    );
}
