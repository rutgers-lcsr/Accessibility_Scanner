import { DomainProvider } from '@/providers/Domain';
import { ReactNode } from 'react';

export default function Layout({ children }: { children: ReactNode }) {
    return <DomainProvider>{children}</DomainProvider>;
}
