'use client';
import PageError from '@/components/PageError';
import PageLoading from '@/components/PageLoading';
import { useRules } from '@/providers/Rules';
import { PlusOutlined } from '@ant-design/icons';
import { FloatButton, Select, Space } from 'antd';
import { useState } from 'react';
import AddRule from './component/AddRule';
import RuleComponent from './component/RuleComponent';

function Rules() {
    const { rules, loading, tags, setTagSearch, error } = useRules();
    const [addModalOpen, setAddModalOpen] = useState(false);

    const showAddModal = () => {
        setAddModalOpen(true);
    };

    return (
        <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <h1 className="text-2xl font-bold mb-4">Accessibility Rules</h1>
            <div className="text-gray-500 mb-4">
                Manage your custom accessibility rules here. You can add, edit, or delete rules to
                tailor the accessibility checks to your needs.
                <FloatButton
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={showAddModal}
                    shape="square"
                    tooltip="Add Rule"
                />
                <AddRule open={addModalOpen} onClose={() => setAddModalOpen(false)} />
                <label className="block mt-4" htmlFor="tag-filter">
                    <Select
                        id="tag-filter"
                        mode="tags"
                        style={{ width: '100%', marginTop: '10px' }}
                        placeholder="Filter by tags"
                        allowClear
                        onChange={(value) => {
                            // Implement tag filtering logic here
                            console.log('Selected tags:', value);
                            setTagSearch(value.join(','));
                        }}
                        options={tags?.map((tag) => ({ label: <span>{tag}</span>, value: tag }))}
                    />
                </label>
            </div>
            {loading && <PageLoading />}
            {error && <PageError title="Error loading rules" />}
            {rules && rules.map((rule) => <RuleComponent key={rule.id} rule={rule} />)}
        </Space>
    );
}

export default Rules;
