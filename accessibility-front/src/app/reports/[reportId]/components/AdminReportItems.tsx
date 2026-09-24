'use client';
import RescanPageButton from '@/components/RescanPageButton';
import { Report } from '@/lib/types/axe';
import { Descriptions, Space, Tooltip } from 'antd';

type Props = {
    report: Report;
};

// The page's actions: rescan it (the website's admin, its members and site admins).
function AdminReportItems({ report }: Props) {
    return (
        <div
            className="mb-4 rounded-md bg-gray-50 p-4 shadow"
            aria-label="Report Overview Information"
        >
            <Space className="w-full" size={'large'} direction="vertical">
                <Descriptions size="small" column={3} layout="horizontal" title="Url Info" bordered>
                    <Descriptions.Item label="Actions">
                        <RescanPageButton siteId={report.site_id} />
                    </Descriptions.Item>
                    <Descriptions.Item label="Tags">
                        <Tooltip
                            title={'Rule tags which are applied to this report'}
                            placement="top"
                        >
                            <span>{report.tags.join(', ')}</span>
                        </Tooltip>
                    </Descriptions.Item>
                </Descriptions>
            </Space>
        </div>
    );
}

export default AdminReportItems;
