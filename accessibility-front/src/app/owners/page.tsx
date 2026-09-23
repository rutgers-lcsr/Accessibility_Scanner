import PageError from '@/components/PageError';
import { User } from '@/lib/types/user';
import { getCurrentUser } from 'next-cas-client/app';
import Owners from './Owners';

async function Page() {
    const user = await getCurrentUser<User>();

    if (!user || !user.is_admin) {
        return (
            <PageError
                status={403}
                title="Access Denied"
                subTitle="You do not have permission to view this page."
            />
        );
    }
    return <Owners />;
}

export default Page;
