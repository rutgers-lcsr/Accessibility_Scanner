'use client';
import PageHeading from '@/components/PageHeading';
import ResourceLink from '@/components/Resource';
import { getAxeLink } from '@/lib/browser';
import { Card } from 'antd';
import Link from 'next/link';
import { ReactNode, useState } from 'react';

const inlineLink = 'font-medium text-[#007fac] underline underline-offset-2 hover:text-[#005f80]';

function SectionHeading({ id, children }: { id: string; children: ReactNode }) {
    return (
        <h2
            id={id}
            className="text-lg tracking-tight text-gray-900"
            style={{ marginTop: 0, marginBottom: 12, fontWeight: 600 }}
        >
            {children}
        </h2>
    );
}

function SubHeading({ children }: { children: ReactNode }) {
    return (
        <h3
            className="text-base text-gray-900"
            style={{ marginTop: 24, marginBottom: 8, fontWeight: 600 }}
        >
            {children}
        </h3>
    );
}

function Bullets({ items }: { items: string[] }) {
    return (
        <ul className="list-disc space-y-1.5 pl-5 marker:text-gray-400" style={{ margin: 0 }}>
            {items.map((item) => (
                <li key={item}>{item}</li>
            ))}
        </ul>
    );
}

export default function Home() {
    // check if browser is chrome or firefox
    const [axeLink] = useState(getAxeLink());

    return (
        <>
            <PageHeading
                title="CS Accessibility Audit Tool"
                subtitle="This tool is for CS department faculty and staff to quickly audit, track, and improve the accessibility of departmental websites and digital resources."
            />
            <div className="mx-auto max-w-6xl space-y-6 px-4 pb-8 leading-relaxed text-gray-800 md:px-6">
                <div className="grid gap-6 lg:grid-cols-5">
                    <Card className="lg:col-span-2">
                        <section aria-labelledby="home-how">
                            <SectionHeading id="home-how">How to Use</SectionHeading>
                            <ol
                                className="list-decimal space-y-2 pl-5 marker:font-semibold marker:text-[#b3002d]"
                                style={{ margin: 0 }}
                            >
                                <li>Request a website.</li>
                                <li>
                                    An administrator will review the request and initiate the audit
                                    process.
                                </li>
                                <li>
                                    You will receive an email with a link to the audit report once
                                    it is complete.
                                </li>
                                <li>Fix issues flagged in the report.</li>
                                <li>Contact CS support for technical help or questions.</li>
                            </ol>
                        </section>
                    </Card>

                    <Card className="lg:col-span-3">
                        <section aria-labelledby="home-resources">
                            <SectionHeading id="home-resources">Support & Resources</SectionHeading>
                            <ul
                                className="grid gap-x-8 divide-y divide-gray-100 sm:grid-cols-2 sm:divide-y-0"
                                style={{ margin: 0, padding: 0, listStyle: 'none' }}
                            >
                                <ResourceLink
                                    title="Rutgers Accessibility website"
                                    description="University-wide accessibility policies, training, and guides."
                                    link="https://accessibility.rutgers.edu/"
                                />
                                <ResourceLink
                                    title="Canvas Accessibility Resources"
                                    description="Resources and guidelines for making Canvas courses accessible."
                                    link="https://canvas.rutgers.edu/canvas-help/accessibility/"
                                />
                                <ResourceLink
                                    title="Rutgers Digital Accessibility Course Content Standards"
                                    description="Minimum Accessibility Standards at the university."
                                    link="https://it.rutgers.edu/digital-accessibility/course-content-bronze/"
                                />
                                <ResourceLink
                                    title="SensusAccess"
                                    description="Tool to convert documents into accessible formats."
                                    link="https://it.rutgers.edu/digital-accessibility/knowledgebase/sensusaccess/"
                                />
                                <ResourceLink
                                    title="Deque Axe DevTools Extension"
                                    description="Browser extension for testing web accessibility."
                                    link={axeLink}
                                />
                                <ResourceLink
                                    title="Interactive Accessibility Help"
                                    description='Learn more about accessibility through interactive tutorials on the "Help" tab.'
                                    link="/help"
                                />
                            </ul>
                        </section>
                    </Card>
                </div>

                <div className="grid gap-6 lg:grid-cols-2">
                    <Card>
                        <section aria-labelledby="home-about">
                            <SectionHeading id="home-about">About Accessibility</SectionHeading>
                            <p style={{ marginBottom: 12 }}>
                                Digital accessibility ensures that websites, tools, and technologies
                                are designed and developed so that people with disabilities can use
                                them. More specifically, people can:
                            </p>
                            <Bullets
                                items={[
                                    'Perceive, understand, navigate, and interact with the website',
                                    'Contribute to and navigate courses',
                                    'Have equal access to information and functionality',
                                    'Use assistive technologies if needed (e.g., screen readers, magnifiers)',
                                    'Have alternative ways to access content (e.g., captions for videos)',
                                    'Experience a user-friendly interface for all users',
                                ]}
                            />
                            <SubHeading>Quick Start: Improving Website Accessibility</SubHeading>
                            <p style={{ marginBottom: 12 }}>
                                The following best practices will help ensure your website is
                                accessible to all users, including those with disabilities. These
                                steps are recommended for all departmental web editors and content
                                managers:
                            </p>
                            <Bullets
                                items={[
                                    'Use clear and descriptive page titles and headings to organize content.',
                                    'Provide alternative (alt) text for all images that conveys their meaning or function.',
                                    'Ensure all links use descriptive text that indicates their destination or purpose.',
                                    'Maintain sufficient color contrast between text and background for readability.',
                                    'Label all form fields clearly and provide instructions where necessary.',
                                    'Do not rely solely on color to convey information.',
                                    'Verify that all site functionality is accessible using only a keyboard.',
                                    'Provide captions for all video content.',
                                ]}
                            />
                        </section>
                    </Card>

                    <Card>
                        <section aria-labelledby="home-rutgers">
                            <SectionHeading id="home-rutgers">Rutgers Requirements</SectionHeading>
                            <p style={{ marginBottom: 12 }}>
                                In addition to the best practices outlined above, all Rutgers
                                websites must comply with the following accessibility standards:
                            </p>
                            <Bullets
                                items={[
                                    'Comply with the Web Content Accessibility Guidelines (WCAG) 2.1 Level AA standards.',
                                    'Ensure that all multimedia content (videos, audio) includes captions and transcripts.',
                                    'Make sure that all documents (PDFs, Word files) are accessible and properly tagged.',
                                    'Regularly test the website using accessibility evaluation tools and address any issues identified.',
                                    'Each page must include an accessibility statement with contact information for reporting issues. See the example below.',
                                ]}
                            />
                            <SubHeading>Official Rutgers Accessibility Statement</SubHeading>
                            <p
                                className="rounded-lg bg-gray-50 px-4 py-3 text-gray-700"
                                style={{ marginBottom: 0 }}
                            >
                                Rutgers is an equal access/equal opportunity institution.
                                Individuals with disabilities are encouraged to direct suggestions,
                                comments, or complaints concerning any accessibility issues with
                                Rutgers web sites to:{' '}
                                <Link
                                    className={inlineLink}
                                    href="mailto:accessibility@rutgers.edu"
                                >
                                    accessibility@rutgers.edu
                                </Link>{' '}
                                or complete the{' '}
                                <Link
                                    className={inlineLink}
                                    href="https://it.rutgers.edu/it-accessibility-initiative/barrierform/"
                                >
                                    Report Accessibility Barrier or Provide Feedback Form
                                </Link>
                                .
                            </p>
                            <SubHeading>For more information on Rutgers Accessibility</SubHeading>
                            <p style={{ marginBottom: 0 }}>
                                Visit the{' '}
                                <Link
                                    className={inlineLink}
                                    href="https://accessibility.rutgers.edu/"
                                >
                                    University Accessibility
                                </Link>{' '}
                                website or view Rutgers Policy 70.1.5,{' '}
                                <Link
                                    className={inlineLink}
                                    href="https://policies.rutgers.edu/B.aspx?BookId=12021&PageId=459372"
                                >
                                    Digital Accessibility
                                </Link>
                                .
                            </p>
                        </section>
                    </Card>
                </div>
            </div>
        </>
    );
}
