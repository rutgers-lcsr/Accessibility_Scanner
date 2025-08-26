'use client';
import '@ant-design/v5-patch-for-react-19';
import { useUser } from '@/providers/User';
import { useWebsites } from '@/providers/Websites';
import { Button, Checkbox, Input, Modal, Select } from 'antd';
import React, { useState } from 'react';
import { Form } from 'antd';

const CreateWebsite: React.FC = () => {
    const { requestWebsite } = useWebsites();
    const { is_admin } = useUser();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [form] = Form.useForm();
    const [shouldEmail, setShouldEmail] = useState(false);

    const showModal = () => {
        setIsModalOpen(true);
    };

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();
            await requestWebsite(values.protocol + values.websiteName, values?.email);

            form.resetFields();
            setIsModalOpen(false);
        } catch (err) {
            // Validation error, do nothing
        }
    };

    return (
        <>
            <Button type="primary" onClick={showModal}>
                {is_admin ? 'Add Website' : 'Request Website'}
            </Button>

            <Modal
                title={is_admin ? 'Add Website' : 'Request Website'}
                open={isModalOpen}
                onCancel={() => setIsModalOpen(false)}
                onOk={handleSubmit}
                okText={is_admin ? 'Add' : 'Request'}
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
                            placeholder="example.com"
                        />
                    </Form.Item>
                    <Form.Item name="should_email" valuePropName="checked">
                        <Checkbox onChange={(e) => setShouldEmail(e.target.checked)}>
                            Email me
                        </Checkbox>
                    </Form.Item>
                    <Form.Item
                        label="Email"
                        name="email"
                        rules={[
                            ({ getFieldValue }) => ({
                                validator(_, value) {
                                    if (!getFieldValue('should_email')) return Promise.resolve();
                                    if (!value)
                                        return Promise.reject(new Error('Please enter your email'));
                                    // Simple email regex
                                    if (!/^\S+@\S+\.\S+$/.test(value))
                                        return Promise.reject(new Error('Invalid email address'));
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
                    </Form.Item>
                </Form>
            </Modal>
        </>
    );
};

export default CreateWebsite;
