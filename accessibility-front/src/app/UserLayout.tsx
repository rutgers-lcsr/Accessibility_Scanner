"use client"
import { UserProvider } from '../providers/User';

export default function UserLayout({ children }: { children: React.ReactNode }) {
    return (
        <UserProvider>
            {children}
        </UserProvider>
    );
}
