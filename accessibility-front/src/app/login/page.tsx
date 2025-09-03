'use client';
import "@ant-design/v5-patch-for-react-19";

import { login } from "next-cas-client";
import React from 'react';
const LoginPage: React.FC = () => {
    login();
    return null;
};

export default LoginPage;
