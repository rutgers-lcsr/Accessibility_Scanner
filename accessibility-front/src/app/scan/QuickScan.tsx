'use client';
import PageHeading from '@/components/PageHeading';
import ScanProgressModal from '@/components/ScanProgressModal';
import { useScan } from '@/hooks/useScan';
import { useUrlFilters } from '@/lib/urlFilters';
import { Button, Card, Form, Input, Select } from 'antd';
import { Content } from 'antd/es/layout/layout';
import QuickScanResult from './QuickScanResult';

// Audit one page ad hoc. The finished task's id goes into the URL (?task=) so the
// result can be reopened or shared with another admin while it lasts.
function QuickScan() {
    const [form] = Form.useForm();
    const { params, setFilters } = useUrlFilters();
    const resultTask = params.get('task');
    const {
        loading,
        taskId,
        statusEndpoint,
        showProgress,
        startScan,
        handleScanComplete,
        handleScanError,
        handleCloseProgress,
    } = useScan({
        quick: true,
        onComplete: () => {
            if (taskId) setFilters({ task: taskId });
        },
    });

    const submit = async () => {
        try {
            const values = await form.validateFields();
            const typed: string = values.url.trim();
            const url = /^https?:\/\//i.test(typed) ? typed : `${values.protocol}${typed}`;
            await startScan(url);
        } catch {
            // validation error: the form shows it
        }
    };

    return (
        <>
            <PageHeading title="Quick Scan" />
            <Content className="p-6">
                <Card className="mb-6">
                    <p className="mb-4 text-gray-700">
                        Check one page before it goes live. Pages under the allowed domains only;
                        nothing is stored and the result expires after a day.
                    </p>
                    <Form form={form} layout="inline" initialValues={{ protocol: 'https://' }}>
                        <Form.Item
                            name="url"
                            rules={[{ required: true, message: 'Enter the page URL' }]}
                            style={{ flex: 1, minWidth: 320 }}
                        >
                            <Input
                                addonBefore={
                                    <Form.Item name="protocol" noStyle>
                                        <Select style={{ width: 90 }} aria-label="Protocol">
                                            <Select.Option value="https://">https://</Select.Option>
                                            <Select.Option value="http://">http://</Select.Option>
                                        </Select>
                                    </Form.Item>
                                }
                                placeholder="cs.rutgers.edu/people"
                                aria-label="Page URL"
                                onPressEnter={submit}
                            />
                        </Form.Item>
                        <Form.Item>
                            <Button
                                type="primary"
                                onClick={submit}
                                loading={loading}
                                disabled={loading}
                            >
                                Scan page
                            </Button>
                        </Form.Item>
                    </Form>
                </Card>
                {resultTask && <QuickScanResult key={resultTask} taskId={resultTask} />}
            </Content>
            {taskId && statusEndpoint && (
                <ScanProgressModal
                    taskId={taskId}
                    statusEndpoint={statusEndpoint}
                    onComplete={handleScanComplete}
                    onError={handleScanError}
                    visible={showProgress}
                    onClose={handleCloseProgress}
                />
            )}
        </>
    );
}

export default QuickScan;
