'use client';
import "@ant-design/v5-patch-for-react-19";

import { useUser } from '@/providers/User';
import { Button, Form, Input, Typography } from 'antd';
import React, { useState } from 'react';
const { Title } = Typography;

const LoginPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const { login } = useUser();

    const onFinish = async (values: { email: string; password: string }) => {
        setLoading(true);
        await login(values.email, values.password);
        setLoading(false);
    };

    return (
        <div className="mx-auto mt-20 h-fit max-w-md rounded-lg bg-white p-6 shadow-lg">
            <Title level={2} className="!mb-8 text-center">
                Login
            </Title>
            <Form name="login" layout="vertical" onFinish={onFinish} requiredMark={false}>
                <Form.Item
                    label="Email"
                    name="email"
                    rules={[{ required: true, message: 'Please input your email!' }]}
                >
                    <Input autoComplete="email" className="!px-3 !py-2" />
                </Form.Item>
                <Form.Item
                    label="Password"
                    name="password"
                    rules={[{ required: true, message: 'Please input your password!' }]}
                >
                    <Input.Password autoComplete="current-password" className="!px-3 !py-2" />
                </Form.Item>
                <Form.Item>
                    <Button
                        type="primary"
                        htmlType="submit"
                        block
                        loading={loading}
                        className="!h-10"
                    >
                        Log in
                    </Button>
                </Form.Item>
            </Form>
        </div>
    );
};

export default LoginPage;
