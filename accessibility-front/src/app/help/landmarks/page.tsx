'use client';

import { Card, Flex, Layout, List, Menu, Typography } from 'antd';

const { Header, Footer, Sider, Content } = Layout;
const { Title, Paragraph, Text } = Typography;

function LandmarksPage() {
    function highlightLandmark(e: React.MouseEvent, landmark: string) {
        e.preventDefault();
        const element = e.currentTarget as HTMLElement;
        element.classList.add('landmark-highlight');

        const overSpan = document.createElement('span');
        overSpan.className = 'landmark-label';
        overSpan.textContent = `<${landmark}>`;

        element.style.position = 'relative';
        element.appendChild(overSpan);

        setTimeout(() => {
            if (element.contains(overSpan)) {
                element.removeChild(overSpan);
            }
        }, 2000);
    }

    function clearHighlight(e: React.MouseEvent) {
        e.preventDefault();
        const element = e.currentTarget as HTMLElement;
        element.classList.remove('landmark-highlight');
    }

    const landmarkList = [
        {
            tag: 'header',
            desc: 'Represents the introductory content or a set of navigational links.',
        },
        {
            tag: 'nav',
            desc: 'Contains navigation links.',
        },
        {
            tag: 'main',
            desc: 'Denotes the main content of the document.',
        },
        {
            tag: 'aside',
            desc: 'Represents content that is tangentially related to the content around it.',
        },
        {
            tag: 'footer',
            desc: 'Contains information about its containing element, typically at the end of the page or section.',
        },
        {
            tag: 'section',
            desc: 'Defines a section in a document, such as chapters, headers, footers, or any other sections of the document.',
        },
        {
            tag: 'article',
            desc: 'Represents a self-contained composition in a document, page, application, or site.',
        },
    ];

    return (
        <>
            <style>
                {`
                    .landmark-highlight {
                        outline: 3px solid #ff9800 !important;
                        outline-offset: 4px;
                        box-shadow: 0 0 0 4px rgba(255,152,0,0.15);
                        z-index: 10;
                        transition: outline 0.2s, box-shadow 0.2s;
                    }
                    .landmark-label {
                        position: absolute;
                        top: 8px;
                        right: 8px;
                        background-color: #ff9800;
                        color: white;
                        padding: 2px 6px;
                        border-radius: 4px;
                        font-size: 0.75rem;
                        font-weight: 600;
                        pointer-events: none;
                        opacity: 0.9;
                        z-index: 20;
                    }
                `}
            </style>
            <Layout className="Example" style={{ minHeight: '100vh', background: '#f9fafb' }}>
                <header
                    onMouseEnter={(e) => highlightLandmark(e, 'header')}
                    onMouseLeave={clearHighlight}
                >
                    <Header
                        style={{
                            background: '#fff',
                            borderRadius: 12,
                            padding: 24,
                        }}
                    >
                        <Title level={1} style={{ margin: 0 }}>
                            Understanding Landmarks in Web Accessibility
                        </Title>
                    </Header>
                </header>
                <nav
                    onMouseEnter={(e) => highlightLandmark(e, 'nav')}
                    onMouseLeave={clearHighlight}
                >
                    <Menu
                        mode="horizontal"
                        items={[
                            {
                                key: 'what-are-landmarks',
                                label: <a href="#what-are-landmarks">What are Landmarks?</a>,
                            },
                            {
                                key: 'why-landmarks-important',
                                label: (
                                    <a href="#why-landmarks-important">
                                        Why are Landmarks Important?
                                    </a>
                                ),
                            },
                            {
                                key: 'best-practices',
                                label: <a href="#best-practices">Best Practices</a>,
                            },
                        ]}
                    />
                </nav>
                <Layout>
                    <main
                        style={{ flex: 1, minHeight: 280 }}
                        onMouseEnter={(e) => highlightLandmark(e, 'main')}
                        onMouseLeave={clearHighlight}
                    >
                        <Content
                            style={{
                                padding: 24,
                                background: '#fff',
                            }}
                        >
                            <Flex gap="24px" align="start" style={{ marginBottom: 24 }}>
                                <section
                                    id="what-are-landmarks"
                                    onMouseEnter={(e) => highlightLandmark(e, 'section')}
                                    onMouseLeave={clearHighlight}
                                >
                                    <Card
                                        title="What are Landmarks?"
                                        extra={
                                            <a href="https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles/landmark_role">
                                                Learn more
                                            </a>
                                        }
                                    >
                                        <Paragraph>
                                            Landmarks are special HTML elements that help define the
                                            structure of a web page. They provide important context
                                            for users, especially those using assistive technologies
                                            like screen readers.
                                        </Paragraph>
                                        <List
                                            dataSource={landmarkList}
                                            renderItem={(item) => (
                                                <List.Item>
                                                    <Text strong>{`<${item.tag}>`}</Text>:{' '}
                                                    {item.desc}
                                                </List.Item>
                                            )}
                                            style={{ marginBottom: 0 }}
                                        />
                                        <Paragraph>
                                            Note: While HTML5 provides several semantic elements
                                            that serve as landmarks, ARIA roles can also be used to
                                            define landmarks when necessary. by using ARIA roles
                                            such as <Text code>role=&quot;banner&quot;</Text>,{' '}
                                            <Text code>role=&quot;navigation&quot;</Text>,{' '}
                                            <Text code>role=&quot;main&quot;</Text>,{' '}
                                            <Text code>role=&quot;complementary&quot;</Text>, and{' '}
                                            <Text code>role=&quot;contentinfo&quot;</Text>.
                                        </Paragraph>
                                        <a href="https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Reference/Roles#landmark_roles">
                                            Learn more
                                        </a>
                                    </Card>
                                </section>
                                <aside
                                    style={{ width: 220, marginRight: 24 }}
                                    onMouseEnter={(e) => highlightLandmark(e, 'aside')}
                                    onMouseLeave={clearHighlight}
                                >
                                    <Sider
                                        width={220}
                                        style={{
                                            background: '#fff',
                                            borderRadius: 12,
                                            padding: 16,
                                            marginTop: 24,
                                            marginBottom: 24,
                                        }}
                                    >
                                        <Title level={4}>Aside Example</Title>
                                        <Paragraph>
                                            This is an <Text code>aside</Text> landmark. It contains
                                            related information or links.
                                        </Paragraph>
                                    </Sider>
                                </aside>
                            </Flex>

                            <article
                                id="why-landmarks-important"
                                onMouseEnter={(e) => highlightLandmark(e, 'article')}
                                onMouseLeave={clearHighlight}
                            >
                                <Card
                                    title="Why are Landmarks Important?"
                                    style={{ marginBottom: 24 }}
                                >
                                    <Paragraph>
                                        Landmarks improve the accessibility of web pages by allowing
                                        users to quickly navigate to different sections. Screen
                                        readers can use landmarks to provide a better browsing
                                        experience, enabling users to jump directly to the main
                                        content or navigation areas without having to go through all
                                        the other content.
                                    </Paragraph>
                                </Card>
                            </article>
                            <section
                                id="best-practices"
                                onMouseEnter={(e) => highlightLandmark(e, 'section')}
                                onMouseLeave={clearHighlight}
                            >
                                <Card title="Best Practices for Using Landmarks">
                                    <List
                                        dataSource={[
                                            'Use landmarks appropriately to define the structure of your page.',
                                            'Ensure that each landmark is used only once per page (e.g., only one <main> element).',
                                            'Provide clear and descriptive labels for landmarks when necessary using ARIA roles or properties.',
                                            'Test your website with screen readers to ensure landmarks are recognized.',
                                        ]}
                                        renderItem={(item) => <List.Item>{item}</List.Item>}
                                    />
                                </Card>
                            </section>
                        </Content>
                    </main>
                </Layout>
                <footer
                    onMouseEnter={(e) => highlightLandmark(e, 'footer')}
                    onMouseLeave={clearHighlight}
                >
                    <Footer style={{ background: '#ffffff', borderRadius: 12, padding: 24 }}>
                        <Text style={{ fontSize: 14 }}>
                            &copy; 2025 LCSR Accessibility Audit Tool. All rights reserved.
                        </Text>
                    </Footer>
                </footer>
            </Layout>
        </>
    );
}

export default LandmarksPage;
