'use client';
import { User } from '@/lib/types/user';
import { useWebsites } from '@/providers/Websites';
import '@ant-design/v5-patch-for-react-19';
import { Button, Form, Input, Modal, Select } from 'antd';
import React, { useState } from 'react';

const CreateWebsite: React.FC<{ user: User|null }> = ({ user }) => {
    const { requestWebsite } = useWebsites();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [form] = Form.useForm();

    const showModal = () => {
        setIsModalOpen(true);
    };

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();
            await requestWebsite(values.protocol + values.websiteName);

            form.resetFields();
            setIsModalOpen(false);
        } catch {
            // Validation error, do nothing
        }
    };

    return (
        <>
            <Button type="primary" onClick={showModal}>
                {user && user.is_admin ? 'Add Website' : 'Request Website'}
            </Button>

            <Modal
                title={user && user.is_admin ? 'Add Website' : 'Request Website'}
                open={isModalOpen}
                onCancel={() => setIsModalOpen(false)}
                onOk={handleSubmit}
                okText={user && user.is_admin ? 'Add' : 'Request'}
            >
                <Form
                    form={form}
                    layout="vertical"
                    initialValues={{ protocol: 'https://' }}
                >
                    <Form.Item
                        label="Website Url"
                        name="websiteName"
                        rules={[{ required: true, message: 'Please enter the website URL' }]}
                    >
                        <Input
                            addonBefore={
                                <Form.Item name="protocol" noStyle>
                                    <Select style={{ width: 90 }}>
                                        <Select.Option value="https://">https://</Select.Option>
                                    </Select>
                                </Form.Item>
                            }
                            placeholder="cs.rutgers.edu"
                        />
                    </Form.Item>
                </Form>
            </Modal>
        </>
    );
};

export default CreateWebsite;
