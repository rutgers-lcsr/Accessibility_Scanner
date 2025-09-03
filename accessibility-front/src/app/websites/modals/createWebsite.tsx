'use client';
import { User } from '@/lib/types/user';
import { useWebsites } from '@/providers/Websites';
import '@ant-design/v5-patch-for-react-19';
import { Button, Checkbox, Divider, Form, Input, Modal, Select, Space } from 'antd';
import React, { useState } from 'react';

const CreateWebsite: React.FC<{ user: User|null }> = ({ user }) => {
    const { requestWebsite } = useWebsites();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [form] = Form.useForm();
    const [shouldEmail, setShouldEmail] = useState(false);

    const showModal = () => {
        setIsModalOpen(true);
    };

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();
            await requestWebsite(values.protocol + values.websiteName, values.should_email);

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
                    initialValues={{ protocol: 'https://', should_email: false }}
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
                    <Divider />
                    <Form.Item label="Notifications" style={{ marginBottom: 0 }}>
                        <Space direction="vertical" size="small">
                            <Form.Item name="should_email" valuePropName="checked" noStyle>
                                <Checkbox onChange={(e) => setShouldEmail(e.target.checked)}>
                                    Email me updates
                                </Checkbox>
                            </Form.Item>
                            {/* <Form.Item
                                name="email"
                                style={{ marginBottom: 0 }}
                                rules={[
                                    ({ getFieldValue }) => ({
                                        validator(_, value) {
                                            if (!getFieldValue('should_email'))
                                                return Promise.resolve();
                                            if (!value)
                                                return Promise.reject(
                                                    new Error('Please enter your email')
                                                );
                                            if (!/^\S+@\S+\.\S+$/.test(value))
                                                return Promise.reject(
                                                    new Error('Invalid email address')
                                                );
                                            return Promise.resolve();
                                        },
                                    }),
                                ]}
                                hidden={!shouldEmail}
                            >
                                <Input
                                    type="email"
                                    placeholder="netid@rutgers.edu"
                                    disabled={!shouldEmail}
                                />
                            </Form.Item> */}
                        </Space>
                    </Form.Item>
                </Form>
            </Modal>
        </>
    );
};

export default CreateWebsite;
