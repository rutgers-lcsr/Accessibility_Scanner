'use client';
import ResourceCard from '@/components/Resource';
import { Card, Carousel, Divider, List, Typography } from 'antd';
import { Content, Header } from 'antd/es/layout/layout';
import Head from 'next/head';

export default function Home() {
    return (
        <>
            <Head>
                <title>LCSR Accessibility Audit Tool</title>
            </Head>
            <Header />
            <Carousel
                arrows
                infinite={true}
                autoplay
                autoplaySpeed={10000}
                easing="ease-in-out"
                waitForAnimate
                className="max-w-7xl mx-auto"
            >
                <Content className="mx-auto p-6" role="main">
                    <Card variant="borderless" style={{ marginTop: 24 }}>
                        <Typography.Title level={2}>CS Accessibility Audit Tool</Typography.Title>
                        <Typography.Paragraph>
                            This tool is for CS department faculty and staff to quickly audit,
                            track, and improve the accessibility of departmental websites and
                            digital resources.
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
                            <a href="mailto:a11y@cs.rutgers.edu">a11y@cs.rutgers.edu</a>.
                        </Typography.Paragraph>
                    </Card>
                </Content>
                <Content className="mx-auto p-6" role="main">
                    <Card variant="borderless" style={{ marginTop: 24 }}>
                        <Typography.Title level={2}>About Accessibility</Typography.Title>
                        <Typography.Paragraph>
                            Digital accessibility ensures that websites, tools, and technologies are
                            designed and developed so that people with disabilities can use them.
                            More specifically, people can:
                        </Typography.Paragraph>
                        <List
                            dataSource={[
                                'Perceive, understand, navigate, and interact with the website',
                                'Contribute to and navigate courses',
                                'Have equal access to information and functionality',
                                'Use assistive technologies if needed (e.g., screen readers, magnifiers)',
                                'Have alternative ways to access content (e.g., captions for videos)',
                                'Experience a user-friendly interface for all users',
                            ]}
                            renderItem={(item) => <List.Item>{item}</List.Item>}
                        />
                        <Divider />
                        <Typography.Title level={4}>
                            Quick Start: Improving Website Accessibility
                        </Typography.Title>
                        <Typography.Paragraph>
                            The following best practices will help ensure your Rutgers website is
                            accessible to all users, including those with disabilities. These steps
                            are recommended for all departmental web editors and content managers:
                        </Typography.Paragraph>
                        <List
                            dataSource={[
                                'Use clear and descriptive page titles and headings to organize content.',
                                'Provide alternative (alt) text for all images that conveys their meaning or function.',
                                'Ensure all links use descriptive text that indicates their destination or purpose.',
                                'Maintain sufficient color contrast between text and background for readability.',
                                'Label all form fields clearly and provide instructions where necessary.',
                                'Do not rely solely on color to convey information.',
                                'Verify that all site functionality is accessible using only a keyboard.',
                                'Provide captions for all video content.',
                            ]}
                            renderItem={(item) => <List.Item>{item}</List.Item>}
                        />
                    </Card>
                </Content>
                <Content className="mx-auto p-6" role="main">
                    <Card variant="borderless" style={{ marginTop: 24 }}>
                        <Typography.Title level={2}>Rutgers Requirements</Typography.Title>
                        <Typography.Paragraph>
                            In addition to the best practices outlined above, all Rutgers websites
                            must comply with the following accessibility standards:
                        </Typography.Paragraph>
                        <List
                            dataSource={[
                                'Comply with the Web Content Accessibility Guidelines (WCAG) 2.1 Level AA standards.',
                                'Ensure that all multimedia content (videos, audio) includes captions and transcripts.',
                                'Make sure that all documents (PDFs, Word files) are accessible and properly tagged.',
                                'Regularly test the website using accessibility evaluation tools and address any issues identified.',
                                'Provide an accessibility statement on the website outlining the commitment to accessibility and contact information for reporting issues. Usually in the footer of the site.',
                            ]}
                            renderItem={(item) => <List.Item>{item}</List.Item>}
                        />
                    </Card>
                </Content>
            </Carousel>
        </>
    );
}
