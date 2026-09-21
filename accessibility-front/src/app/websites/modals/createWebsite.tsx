'use client';
import { APIError } from '@/lib/api';
import { PublicUser } from '@/lib/types/user';
import { NewWebsiteOptions, useWebsites } from '@/providers/Websites';
import { Button, Form, Input, Modal, Select } from 'antd';
import React, { useState } from 'react';

const CreateWebsite: React.FC<{ user: PublicUser | null }> = ({ user }) => {
    const { requestWebsite, categories } = useWebsites();
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    // Host the API refused because it is not under an allowed domain yet; a site admin
    // is asked whether to allow-list it and continue.
    const [missingDomain, setMissingDomain] = useState<string | null>(null);
    const [form] = Form.useForm();
    const isAdmin = !!user?.is_admin;

    const showModal = () => {
        setIsModalOpen(true);
    };

    const submit = async (createDomain = false) => {
        try {
            setLoading(true);
            const values = await form.validateFields();
            const options: NewWebsiteOptions = {};
            if (isAdmin) {
                if (values.admin?.trim()) options.admin = values.admin.trim();
                if (values.categories?.length) options.categories = values.categories;
                if (createDomain) options.create_domain = true;
            }
            const website = await requestWebsite(values.protocol + values.websiteName, options);
            if (website) {
                form.resetFields();
                setIsModalOpen(false);
            }
        } catch (error) {
            const domain = (error as APIError).details?.domain;
            if (isAdmin && typeof domain === 'string') {
                setMissingDomain(domain);
            }
            // Otherwise a validation error, which the form already shows
        } finally {
            setLoading(false);
        }
    };

    return (
        <>
            <Button type="primary" onClick={showModal}>
                {isAdmin ? 'Add Website' : 'Request Website'}
            </Button>

            <Modal
                confirmLoading={loading}
                title={isAdmin ? 'Add Website' : 'Request Website'}
                open={isModalOpen}
                onCancel={() => setIsModalOpen(false)}
                onOk={() => submit()}
                okText={isAdmin ? 'Add' : 'Request'}
            >
                <Form form={form} layout="vertical" initialValues={{ protocol: 'https://' }}>
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
                            onPressEnter={() => submit()}
                        />
                    </Form.Item>
                    {isAdmin && (
                        <>
                            <Form.Item
                                label="Admin User"
                                name="admin"
                                extra="Username of the website's admin. Leave empty to make yourself the admin."
                            >
                                <Input placeholder={user?.username} />
                            </Form.Item>
                            <Form.Item label="Categories" name="categories">
                                <Select
                                    mode="tags"
                                    placeholder="Add or select categories"
                                    options={(categories ?? []).map((category) => ({
                                        label: category,
                                        value: category,
                                    }))}
                                />
                            </Form.Item>
                        </>
                    )}
                </Form>
            </Modal>

            <Modal
                title="Domain not allowed yet"
                open={missingDomain !== null}
                confirmLoading={loading}
                okText="Add domain and website"
                onOk={async () => {
                    await submit(true);
                    setMissingDomain(null);
                }}
                onCancel={() => setMissingDomain(null)}
            >
                <p>
                    Websites can only be added under an allowed domain, and{' '}
                    <strong>{missingDomain}</strong> is not one yet.
                </p>
                <p>Add it as an allowed domain and create the website?</p>
            </Modal>
        </>
    );
};

export default CreateWebsite;
