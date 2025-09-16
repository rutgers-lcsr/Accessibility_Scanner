import PageError from '@/components/PageError';
import { User } from '@/lib/types/user';
import { getCurrentUser } from 'next-cas-client/app';
import Rules from './Rules';

async function page() {
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
    return (
        <div>
            <Rules />
        </div>
    );
}

export default page;
