'use client';

import { Flex } from 'antd';
import Card from 'antd/es/card/Card';

function HelpPage() {
    return (
        <>
            <Flex justify="center" align="center">
                <Card
                    variant="borderless"
                    style={{ maxWidth: 400, minWidth: 300, margin: 16 }}
                    title={
                        <span role="heading" aria-level={2}>
                            Landmarks
                        </span>
                    }
                    extra={
                        <a href="/help/landmarks" aria-label="Learn more about Landmarks">
                            Learn more
                        </a>
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
