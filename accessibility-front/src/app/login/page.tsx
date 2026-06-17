'use client';
import { login } from 'next-cas-client';
import React from 'react';
const LoginPage: React.FC = () => {
    React.useEffect(() => {
        login();
    }, []);
    return null;
};

export default LoginPage;
