import PageError from '@/components/PageError';
import { User } from '@/lib/types/user';
import { getCurrentUser } from 'next-cas-client/app';
import QuickScan from './QuickScan';

export default async function Page() {
    const user = await getCurrentUser<User>();

    if (!user) {
        return (
            <PageError
                status={403}
                title="Access Denied"
                subTitle="You must be logged in to run a quick scan."
            />
        );
    }
    return <QuickScan />;
}
