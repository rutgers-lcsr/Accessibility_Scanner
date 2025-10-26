'use client';
import PageError from '@/components/PageError';
import PageHeading from '@/components/PageHeading';
import PageLoading from '@/components/PageLoading';
import { useRules } from '@/providers/Rules';
import { PlusOutlined } from '@ant-design/icons';
import { Flex, FloatButton, Select, Space } from 'antd';
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
        <>
            <PageHeading title="Accessibility Rules" />
            <Flex justify="center" align="stretch" style={{ width: '100%' }}>
                <Space direction="vertical" size="large" style={{ alignContent: 'center' }}>
                    <div className="text-gray-600 mb-4">
                        Manage your custom accessibility rules here. You can add, edit, or delete
                        rules to tailor the accessibility checks to your needs.
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
                                aria-label="Tags Select"
                                allowClear
                                onChange={(value) => {
                                    // Implement tag filtering logic here
                                    setTagSearch(value.join(','));
                                }}
                                options={tags?.map((tag) => ({
                                    label: <span>{tag}</span>,
                                    value: tag,
                                }))}
                            />
                        </label>
                    </div>
                    {loading && <PageLoading />}
                    {error && <PageError title="Error loading rules" />}
                    {rules && rules.map((rule) => <RuleComponent key={rule.id} rule={rule} />)}
                </Space>
            </Flex>
        </>
    );
}

export default Rules;
