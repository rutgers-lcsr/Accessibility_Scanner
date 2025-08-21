import { WebsitesProvider } from "@/providers/Websites";
import { ReactNode } from "react";

export default function Layout({ children }: { children: ReactNode }) {
    return (
        <WebsitesProvider>
            <div className="p-4 w-full" role="main">{children}</div>
        </WebsitesProvider>
    );
}
