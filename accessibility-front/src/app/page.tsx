'use client';
import { Card, Divider, List, Typography } from 'antd';
import { Content, Header } from 'antd/es/layout/layout';
import Head from 'next/head';

export default function Home() {
    return (
        <>
            <Head>
                <title>LCSR Accessibility Audit Tool</title>
            </Head>
            <Header />
            <Content className="mx-auto max-w-3xl p-6" role="main">
                <Card variant="borderless" style={{ marginTop: 24 }}>
                    <Typography.Title level={2}>CS Accessibility Audit Tool</Typography.Title>
                    <Typography.Paragraph>
                        This tool is for CS department faculty and staff to quickly audit, track,
                        and improve the accessibility of departmental websites and digital
                        resources.
                    </Typography.Paragraph>
                    <Divider />
                    <Typography.Title level={4}>How to Use</Typography.Title>
                    <List
                        dataSource={[
                            'Add or request a CS department website for audit using the menu.',
                            'An Admin will review the request and initiate the audit process.',
                            'Fix issues flagged in the report.',
                            'Contact CS support for technical help or questions.',
                        ]}
                        renderItem={(item) => <List.Item>{item}</List.Item>}
                    />
                    <Divider />
                    <Typography.Title level={4}>Support & Resources</Typography.Title>
                    <Typography.Paragraph>
                        For technical help, email{' '}
                        <a href="mailto:help@cs.rutgers.edu">help@cs.rutgers.edu</a>.<br />
                        For university-wide accessibility policies, training, and guides, visit the{' '}
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
