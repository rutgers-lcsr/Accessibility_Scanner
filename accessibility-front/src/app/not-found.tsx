import PageError from '@/components/PageError';
import { Header } from 'antd/es/layout/layout';

export default function NotFound() {
    return (
        <>
            <title>Page Not Found - 404</title>
            <Header />
            <PageError
                status={404}
                title="Page Not Found"
                subTitle="Sorry, the page you are looking for does not exist."
            />
        </>
    );
}
