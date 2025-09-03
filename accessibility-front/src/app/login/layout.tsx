import { Header } from 'antd/es/layout/layout';
import { getCurrentUser } from 'next-cas-client/app';
import { redirect } from 'next/navigation';
import { ReactNode } from 'react';

export default async function Layout({ children }: { children: ReactNode }) {

    const user = await getCurrentUser();
    if (user){
        // If user is logged in, redirect to home page
        redirect('/');  
    }


    return (
        <>
            <Header></Header>
            {children}
        </>
    );
}