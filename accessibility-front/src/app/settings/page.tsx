import PageError from '@/components/PageError';
import { User } from '@/lib/types/user';
import { getCurrentUser } from 'next-cas-client/app';
import SettingsTabs from './components/SettingsTabs';

export default async function page() {
    const user = await getCurrentUser<User>();

    if (!user) {
        return (
            <PageError
                status={403}
                title="Access Denied"
                subTitle="You must be logged in to view this page."
            />
        );
    }
    return <SettingsTabs isAdmin={user.is_admin} />;
}
