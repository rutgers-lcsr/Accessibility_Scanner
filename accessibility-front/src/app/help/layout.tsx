import PageHeading from '@/components/PageHeading';
import { Content } from 'antd/es/layout/layout';
import { ReactNode } from 'react';

export default async function Layout({ children }: { children: ReactNode }) {
    return (
        <>
            <PageHeading title="Help & Documentation" />
            <Content>{children}</Content>
        </>
    );
}
