import { LoadingOutlined } from '@ant-design/icons';
import { Flex, Spin } from 'antd';

export default function PageLoading() {
    return (
        <div className="flex h-screen items-center justify-center">
            <Flex align="center" gap="middle">
                <Spin
                    tip="Loading..."
                    fullscreen
                    indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />}
                />
            </Flex>
        </div>
    );
}
