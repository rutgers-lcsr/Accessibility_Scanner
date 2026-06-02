'use client';
import PageHeading from '@/components/PageHeading';
import { SettingsProvider } from '@/providers/Settings';
import { ApiOutlined, SettingOutlined } from '@ant-design/icons';
import { Tabs } from 'antd';
import ApiKeys from './ApiKeys';
import Settings from './Settings';

function SettingsTabs({ isAdmin }: { isAdmin: boolean }) {
    const items = [
        {
            key: 'api-keys',
            label: (
                <span>
                    <ApiOutlined /> API Keys
                </span>
            ),
            children: <ApiKeys />,
        },
    ];

    if (isAdmin) {
        items.push({
            key: 'application',
            label: (
                <span>
                    <SettingOutlined /> Application
                </span>
            ),
            children: (
                <SettingsProvider>
                    <Settings />
                </SettingsProvider>
            ),
        });
    }

    return (
        <>
            <PageHeading title="Settings" />
            <div className="mt-13 w-full p-6">
                <Tabs items={items} />
            </div>
        </>
    );
}

export default SettingsTabs;
