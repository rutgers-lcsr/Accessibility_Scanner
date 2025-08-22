import { WebsitesProvider } from "@/providers/Websites";
import { Header } from "antd/es/layout/layout";
import { ReactNode } from "react";

export default function Layout({ children }: { children: ReactNode }) {
    return (
        <>
            <WebsitesProvider>
                <Header>
                    <h1>Websites</h1>
                </Header>
                <div className="p-4" role="main">{children}</div>
            </WebsitesProvider>
        </>

    );
}
