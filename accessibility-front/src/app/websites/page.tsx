import Website from '@/app/websites/components/Website';
import { User, toPublicUser } from '@/lib/types/user';
import { getCurrentUser } from 'next-cas-client/app';
import Websites from './Websites';
export default async function Page({
    searchParams,
}: {
    searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
    const user = toPublicUser(await getCurrentUser<User>());
    const websiteId = (await searchParams).id;

    if (websiteId) {
        return <Website user={user} websiteId={Number(websiteId)} />;
    }

    return <Websites user={user} />;
}
