'use client';
import { TaskStatus } from '@/lib/types/scan';
import { useUser } from '@/providers/User';
import {
    CheckCircleOutlined,
    CloseCircleOutlined,
    LoadingOutlined,
    SyncOutlined,
} from '@ant-design/icons';
import { Alert, Modal, Progress, Space, Spin, Tag } from 'antd';
import { useEffect, useState } from 'react';

type Props = {
    taskId: string;
    statusEndpoint: string;
    onComplete?: () => void;
    onError?: (error: string) => void;
    visible: boolean;
    onClose: () => void;
};

const ScanProgressModal = ({
    taskId,
    statusEndpoint,
    onComplete,
    onError,
    visible,
    onClose,
}: Props) => {
    const { handlerUserApiRequest } = useUser();
    const [taskStatus, setTaskStatus] = useState<TaskStatus | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!visible || !taskId) return;

        const pollTaskStatus = async () => {
            try {
                const status = await handlerUserApiRequest<TaskStatus>(statusEndpoint, {
                    method: 'GET',
                });

                setTaskStatus(status);

                if (status.state === 'SUCCESS') {
                    clearInterval(intervalId);
                    if (onComplete) {
                        onComplete();
                    }
                } else if (status.state === 'FAILURE') {
                    clearInterval(intervalId);
                    const errorMsg = status.status || 'Scan failed';
                    setError(errorMsg);
                    if (onError) {
                        onError(errorMsg);
                    }
                }
            } catch (err) {
                console.error('Error polling task status:', err);
                setError('Failed to fetch task status');
            }
        };

        // Initial poll
        pollTaskStatus();

        // Poll every 2 seconds
        const intervalId = setInterval(pollTaskStatus, 2000);

        return () => {
            if (intervalId) {
                clearInterval(intervalId);
            }
        };
    }, [taskId, statusEndpoint, visible, onComplete, onError, handlerUserApiRequest]);

    const getStateIcon = () => {
        switch (taskStatus?.state) {
            case 'SUCCESS':
                return <CheckCircleOutlined style={{ fontSize: 48, color: '#52c41a' }} />;
            case 'FAILURE':
                return <CloseCircleOutlined style={{ fontSize: 48, color: '#ff4d4f' }} />;
            case 'PROGRESS':
                return <LoadingOutlined style={{ fontSize: 48, color: '#1890ff' }} />;
            default:
                return <SyncOutlined spin style={{ fontSize: 48, color: '#1890ff' }} />;
        }
    };

    const getStateTag = () => {
        switch (taskStatus?.state) {
            case 'SUCCESS':
                return <Tag color="success">Completed</Tag>;
            case 'FAILURE':
                return <Tag color="error">Failed</Tag>;
            case 'PROGRESS':
                return <Tag color="processing">In Progress</Tag>;
            case 'PENDING':
                return <Tag color="default">Pending</Tag>;
            default:
                return <Tag>{taskStatus?.state}</Tag>;
        }
    };

    const getProgressPercent = () => {
        if (!taskStatus) return 0;
        if (taskStatus.state === 'SUCCESS') return 100;
        if (taskStatus.state === 'FAILURE') return 0;
        if (taskStatus.state === 'PENDING') return 0;

        // For PROGRESS state
        if (taskStatus.total && taskStatus.total > 0) {
            const current = taskStatus.current || 0;
            return Math.round((current / taskStatus.total) * 100);
        }

        // If total is 0 or undefined, show indeterminate progress
        return 0;
    };

    return (
        <Modal
            title="Scan Progress"
            open={visible}
            onCancel={onClose}
            footer={null}
            width={600}
            centered
        >
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
                <div style={{ textAlign: 'center' }}>{getStateIcon()}</div>

                <div style={{ textAlign: 'center' }}>
                    <Space direction="vertical" size="small">
                        <div>
                            <strong>Task ID:</strong> <code>{taskId}</code>
                        </div>
                        <div>Status: {getStateTag()}</div>
                    </Space>
                </div>

                {taskStatus?.state === 'PROGRESS' && (
                    <div>
                        {taskStatus.total && taskStatus.total > 0 ? (
                            <>
                                <Progress
                                    percent={getProgressPercent()}
                                    status="active"
                                    strokeColor={{
                                        '0%': '#108ee9',
                                        '100%': '#87d068',
                                    }}
                                />
                                <div style={{ marginTop: 4, textAlign: 'center', fontSize: 12 }}>
                                    {taskStatus.current || 0} / {taskStatus.total} pages scanned
                                </div>
                            </>
                        ) : (
                            <Progress
                                percent={50}
                                status="active"
                                showInfo={false}
                                strokeColor={{
                                    '0%': '#108ee9',
                                    '100%': '#87d068',
                                }}
                            />
                        )}
                        {taskStatus.status && (
                            <div style={{ marginTop: 8, textAlign: 'center', color: '#666' }}>
                                {taskStatus.status}
                            </div>
                        )}
                    </div>
                )}

                {taskStatus?.state === 'PENDING' && (
                    <div style={{ textAlign: 'center' }}>
                        <Spin tip="Waiting for worker to pick up task..." />
                        <div style={{ marginTop: 12, color: '#666' }}>
                            {taskStatus.status || 'Task queued...'}
                        </div>
                    </div>
                )}

                {taskStatus?.state === 'SUCCESS' && taskStatus.result && (
                    <Alert
                        message="Scan Completed Successfully!"
                        description={
                            <div>
                                <p>
                                    <strong>Website:</strong> {taskStatus.result.website_url}
                                </p>
                                <p>
                                    <strong>Reports Generated:</strong>{' '}
                                    {taskStatus.result.reports_generated}
                                </p>
                                <p>
                                    <strong>Sites Scanned:</strong>{' '}
                                    {taskStatus.result.sites_scanned}
                                </p>
                            </div>
                        }
                        type="success"
                        showIcon
                    />
                )}

                {(taskStatus?.state === 'FAILURE' || error) && (
                    <Alert
                        message="Scan Failed"
                        description={error || taskStatus?.status || 'An unknown error occurred'}
                        type="error"
                        showIcon
                    />
                )}
            </Space>
        </Modal>
    );
};

export default ScanProgressModal;
