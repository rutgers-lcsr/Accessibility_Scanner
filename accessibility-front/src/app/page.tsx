'use client';
import { Content, Header } from 'antd/es/layout/layout';
import { Card, List, Typography, Divider } from 'antd';
import Head from 'next/head';

export default function Home() {
    return (
        <>
            <Head>
                <title>LCSR Accessibility Audit Tool</title>
            </Head>
            <Header></Header>
            <Content className="mx-auto max-w-3xl p-6" role="main">
                <Card variant="borderless" style={{ marginTop: 24 }}>
                    <Typography.Title level={2}>
                        Welcome to the LCSR Accessibility Audit Tool
                    </Typography.Title>
                    <Typography.Paragraph>
                        This tool is designed to make it easy for Faculty and Staff in the CS
                        department to audit and improve the accessibility of their websites and
                        digital resources.
                    </Typography.Paragraph>
                    <Divider />
                    <Typography.Title level={4}>Key Features</Typography.Title>
                    <List
                        dataSource={[
                            'Scan your website for accessibility issues',
                            'Get actionable recommendations for fixes',
                            'Track your audit history and progress',
                            'Request help or report a new website',
                        ]}
                        renderItem={(item) => <List.Item>{item}</List.Item>}
                    />
                    <Divider />
                    <Typography.Title level={4}>How to Get Started</Typography.Title>
                    <List
                        dataSource={[
                            'Use the menu to add or request a website for audit.',
                            'Review the accessibility report and follow the recommendations.',
                            'Contact support if you need assistance or have questions.',
                        ]}
                        renderItem={(item) => <List.Item>{item}</List.Item>}
                    />
                    <Divider />
                    <Typography.Title level={4}>Support & Resources</Typography.Title>
                    <Typography.Paragraph>
                        For help, contact{' '}
                        <a href="mailto:help@cs.rutgers.edu">help@cs.rutgers.edu</a> or visit the{' '}
                        <a href="https://accessibility.rutgers.edu/">
                            Rutgers Accessibility website
                        </a>
                        .
                    </Typography.Paragraph>
                </Card>
            </Content>
        </>
    );
}
