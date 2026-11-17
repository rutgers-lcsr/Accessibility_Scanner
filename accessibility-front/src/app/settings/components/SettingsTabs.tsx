'use client';
import PageHeading from '@/components/PageHeading';
import { SettingsProvider } from '@/providers/Settings';
import {
    ApiOutlined,
    CheckSquareOutlined,
    ExceptionOutlined,
    SettingOutlined,
    ShopOutlined,
} from '@ant-design/icons';
import { Tabs } from 'antd';
import ApiKeys from './ApiKeys';
import ExceptionsRegister from './ExceptionsRegister';
import Requirements from './Requirements';
import Vendors from './Vendors';
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
        items.push({
            key: 'requirements',
            label: (
                <span>
                    <CheckSquareOutlined /> Content requirements
                </span>
            ),
            children: <Requirements />,
        });
        items.push({
            key: 'vendors',
            label: (
                <span>
                    <ShopOutlined /> Vendors
                </span>
            ),
            children: <Vendors />,
        });
        items.push({
            key: 'exceptions',
            label: (
                <span>
                    <ExceptionOutlined /> Exceptions
                </span>
            ),
            children: <ExceptionsRegister />,
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
