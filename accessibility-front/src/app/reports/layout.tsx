import { ReportsProvider } from "@/providers/Reports";
import { ReactNode } from "react";

export default function Layout({ children }: { children: ReactNode }) {
    return (
        <ReportsProvider>
            <div className="p-4 w-full" role="main">{children}</div>
        </ReportsProvider>
    );
}
