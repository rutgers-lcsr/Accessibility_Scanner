import Website from '@/app/websites/components/Website';
import { User, toPublicUser } from '@/lib/types/user';
import type { Metadata } from 'next';
import { getCurrentUser } from 'next-cas-client/app';

// The browser tab and screen readers name the page by its website.
export async function generateMetadata({
    params,
}: {
    params: Promise<{ websiteId: string }>;
}): Promise<Metadata> {
    const { websiteId } = await params;
    const user = await getCurrentUser<User>();
    try {
        const response = await fetch(`${process.env.API_URL}/api/websites/${websiteId}/`, {
            headers: user ? { Authorization: `Bearer ${user.access_token || ''}` } : undefined,
        });
        if (!response.ok) return { title: 'Website report' };
        const website = (await response.json()) as { url: string };
        return { title: `${website.url.replace(/^https?:\/\//, '')} – website report` };
    } catch {
        return { title: 'Website report' };
    }
}

async function page({ params }: { params: Promise<{ websiteId: string }> }) {
    const { websiteId } = await params;
    const user = toPublicUser(await getCurrentUser<User>());
    return <Website user={user} websiteId={Number(websiteId)} />;
}

export default page;
