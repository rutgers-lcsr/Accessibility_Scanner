"use client"
import { useWebsites } from '@/providers/Websites';
import Pagination from 'antd/es/pagination/Pagination';
import { Input } from 'antd';
import { useSearchParams } from 'next/navigation';
import Website from '@/components/Website';
export default function Page() {
    const searchParams = useSearchParams();
    const { websites, setWebsitePage, setWebsiteLimit, WebsitePage, isLoading, setWebsiteSearch } = useWebsites();

    const id = searchParams.get('id');

    if (id) {
        return <Website websiteId={Number(id)} />;
    }





    return <div className=''>
        <header className='flex mb-4 w-full justify-between'>
            <h1 className='text-2xl font-bold'>Websites</h1>
            <div>
                <Input.Search className='w-64' placeholder="Search websites" onSearch={(value) => setWebsiteSearch(value)} loading={isLoading} />

            </div>
        </header>
        <main className='h-[calc(100vh-8rem)] overflow-y-auto'>
            <table className="w-full border-collapse">
                <thead>
                    <tr className="bg-gray-100">
                        <th className="text-left p-1 border-b">URL</th>
                        <th className="text-left p-1 border-b">Last Scanned</th>
                        <th className="text-left p-1 border-b">Active</th>
                    </tr>
                </thead>
                <tbody>
                    {websites && websites.length > 0 ? (
                        websites.map((website) => (
                            <tr key={website.id} className="even:bg-gray-50">
                                <td className="p-2">
                                    <a href={`/websites?id=${website.id}`}>{website.base_url}</a>
                                </td>
                                <td className="p-2  text-sm text-gray-500">
                                    {new Date(website.last_scanned).toLocaleDateString()}
                                </td>
                                <td className="p-2 text-sm text-gray-500">
                                    {website.active ? 'Yes' : 'No'}
                                </td>
                            </tr>
                        ))
                    ) : (
                        <tr>
                            <td colSpan={3} className="p-2 text-center text-gray-500">
                                No websites found.
                            </td>
                        </tr>
                    )}
                </tbody>
            </table>
        </main>
        <footer className="mt-4 justify-center flex">
            <Pagination showSizeChanger defaultCurrent={WebsitePage} total={websites?.length || 0} onShowSizeChange={(current, pageSize) => {
                setWebsitePage(current);
                setWebsiteLimit(pageSize);
            }} />
        </footer>
    </div>;
}