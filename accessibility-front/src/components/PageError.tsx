import { Button, Result } from 'antd';
import { ResultStatusType } from 'antd/es/result';
import React from 'react';

interface PageErrorProps {
    status?: ResultStatusType;
    title?: string;
    subTitle?: string;
    onRetry?: () => void;
}

const PageError: React.FC<PageErrorProps> = ({
    status = 500,
    title = 'Something went wrong',
    subTitle = 'Please try again later.',
    onRetry,
}) => (
    <Result
        status={status}
        title={title}
        subTitle={subTitle}
        extra={
            onRetry && (
                <Button type="primary" onClick={onRetry}>
                    Retry
                </Button>
            )
        }
    />
);

export default PageError;
