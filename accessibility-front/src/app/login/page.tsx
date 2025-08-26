'use client';

import React, { useState } from 'react';
import { Form, Input, Button, Typography, message } from 'antd';
import { useRouter } from 'next/navigation';
import { useUser } from '@/providers/User';
import { Header } from 'antd/es/layout/layout';
const { Title } = Typography;

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);

  const router = useRouter();
  const { login } = useUser();

  const onFinish = (values: { email: string; password: string }) => {
    setLoading(true);
    login(values.email, values.password)
      .then((user) => {
        router.push('/'); // Redirect to home page after successful login
      })
      .catch((error) => {
        message.error(`Login failed: ${error.message}`);
      })
      .finally(() => {
        setLoading(false);
      });
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
          <Button type="primary" htmlType="submit" block loading={loading} className="!h-10">
            Log in
          </Button>
        </Form.Item>
      </Form>
    </div>
  );
};

export default LoginPage;
