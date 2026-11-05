'use client';
import ScanProgressModal from '@/components/ScanProgressModal';
import { useScan } from '@/hooks/useScan';
import { Button } from 'antd';

type Props = {
    websiteId: number;
    onComplete: () => void;
};

// Scans the whole website and shows the progress. Sits in the page heading for the people
// who may scan it: site admins, the website's admin and its members.
function ScanWebsiteButton({ websiteId, onComplete }: Props) {
    const {
        loading,
        taskId,
        statusEndpoint,
        showProgress,
        startScan,
        handleScanComplete,
        handleScanError,
        handleCloseProgress,
    } = useScan({ websiteId, onComplete });

    return (
        <>
            <Button type="primary" loading={loading} onClick={() => startScan()} disabled={loading}>
                {loading ? 'Scanning...' : 'Scan Website'}
            </Button>
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

export default ScanWebsiteButton;
