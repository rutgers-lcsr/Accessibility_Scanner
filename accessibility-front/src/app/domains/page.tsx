
import PageError from '@/components/PageError';
import { getCurrentUser } from 'next-cas-client/app';
import Domains from './domains';
// type Props = {}

async function Page() {

    const user = await getCurrentUser();


    if (!user){
        return <PageError status={403} title="Access Denied" subTitle="You do not have permission to view this page." />;
    }
    return <Domains />;
}

export default Page;
