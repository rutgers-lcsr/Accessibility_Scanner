import Website from '@/app/websites/components/Website';
import { User, toPublicUser } from '@/lib/types/user';
import { getCurrentUser } from 'next-cas-client/app';

async function page({ params }: { params: Promise<{ websiteId: string }> }) {
    const { websiteId } = await params;
    const user = toPublicUser(await getCurrentUser<User>());
    return <Website user={user} websiteId={Number(websiteId)} />;
}

export default page;
