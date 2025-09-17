'use client';
import ResourceCard from '@/components/Resource';
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
            <Content className="mx-auto p-6" role="main">
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
                            'Request a website.',
                            'An administrator will review the request and initiate the audit process.',
                            'You will receive an email with a link to the audit report once it is complete.',
                            'Fix issues flagged in the report.',
                            'Contact CS support for technical help or questions.',
                        ]}
                        renderItem={(item) => <List.Item>{item}</List.Item>}
                    />
                    <Divider />
                    <Typography.Title level={4}>Support & Resources</Typography.Title>
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-2 max-w-4xl">
                        <ResourceCard
                            title="Rutgers Accessibility website"
                            description="University-wide accessibility policies, training, and guides."
                            link="https://accessibility.rutgers.edu/"
                        />
                        <ResourceCard
                            title="Canvas Accessibility Resources"
                            description="Resources and guidelines for making Canvas courses accessible."
                            link="https://canvas.rutgers.edu/canvas-help/accessibility/"
                        />
                        <ResourceCard
                            title="Rutgers Digital Accessibility Course Content Standards"
                            description="Minimum Accessibility Standards at the university."
                            link="https://it.rutgers.edu/digital-accessibility/course-content-bronze/"
                        />
                        <ResourceCard
                            title="SensusAccess"
                            description="Tool to convert documents into accessible formats."
                            link="https://it.rutgers.edu/digital-accessibility/knowledgebase/sensusaccess/"
                        />
                        <ResourceCard
                            title="Deque Axe DevTools for Chrome"
                            description="Browser extension for testing web accessibility."
                            link="https://chromewebstore.google.com/detail/axe-devtools-web-accessib/lhdoppojpmngadmnindnejefpokejbdd"
                        />
                    </div>
                    <Divider />
                    <Typography.Title level={4}>Additional Help</Typography.Title>
                    <Typography.Paragraph>
                        For technical assistance, contact the LCSR at{' '}
                        <a href="mailto:help@cs.rutgers.edu">help@cs.rutgers.edu</a>.
                    </Typography.Paragraph>
                </Card>
            </Content>
        </>
    );
}
