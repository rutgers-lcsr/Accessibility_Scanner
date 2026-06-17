'use client';

import { Flex } from 'antd';
import Card from 'antd/es/card/Card';
import Link from 'next/link';

function HelpPage() {
    return (
        <>
            <Flex justify="center" align="center">
                <Card
                    variant="borderless"
                    style={{ maxWidth: 400, minWidth: 300, margin: 16 }}
                    title={<h2>Landmarks</h2>}
                    extra={
                        <Link href="/help/landmarks" aria-label="Learn more about Landmarks">
                            Learn more
                        </Link>
                    }
                    tabIndex={0}
                    aria-describedby="landmarks-desc"
                >
                    <p id="landmarks-desc">
                        Landmarks help users, especially those using assistive technologies, to
                        quickly understand the page structure and navigate content efficiently.
                    </p>
                </Card>
            </Flex>
        </>
    );
}

export default HelpPage;
