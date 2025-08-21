'use client';
import React, { useState } from 'react';
import { Form, Input, Button, Typography, message } from 'antd';
import { useRouter } from 'next/navigation';
const { Title } = Typography;

const LoginPage: React.FC = () => {
    const [loading, setLoading] = useState(false);
    const router = useRouter();

    const onFinish = (values: { username: string; password: string }) => {
        setLoading(true);
        setTimeout(() => {
            setLoading(false);
            message.success('Login successful!');
            router.push('/dashboard');
        }, 1000);
    };

    return (
        <div className="max-w-md mx-auto mt-20 p-6 h-fit bg-white rounded-lg shadow-lg">
            <Title level={2} className="text-center !mb-8">Login</Title>
            <Form
                name="login"
                layout="vertical"
                onFinish={onFinish}
                requiredMark={false}
            >
                <Form.Item
                    label="Email"
                    name="email"
                    rules={[{ required: true, message: 'Please input your email!' }]}
                >
                    <Input autoComplete="email" className="!py-2 !px-3" />
                </Form.Item>
                <Form.Item
                    label="Password"
                    name="password"
                    rules={[{ required: true, message: 'Please input your password!' }]}
                >
                    <Input.Password autoComplete="current-password" className="!py-2 !px-3" />
                </Form.Item>
                <Form.Item>
                    <Button type="primary" htmlType="submit" block loading={loading} className="!h-10">
                        Log in
                    </Button>
                </Form.Item>
            </Form>
        </div>
    );
};

export default LoginPage;
