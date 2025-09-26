import { SettingsProvider } from '@/providers/Settings';
import { ReactNode } from 'react';

export default async function Layout({ children }: { children: ReactNode }) {
    return <SettingsProvider>{children}</SettingsProvider>;
}
