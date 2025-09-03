import Website from '@/components/Website';
import { User } from '@/lib/types/user';
import { getCurrentUser } from 'next-cas-client/app';
import Websites from './Websites';
export default async function Page({searchParams}: {searchParams: Promise<{ [key: string]: string | string[] | undefined }>}) {

    const user: User | null = await getCurrentUser();
    const websiteId = (await searchParams).id;

    if (websiteId) {
        return <Website user={user} websiteId={Number(websiteId)} />;
    }

    return <Websites user={user} />;
}
