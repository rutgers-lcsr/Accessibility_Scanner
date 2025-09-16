import { LoadingOutlined } from '@ant-design/icons';
import { Flex, Spin } from 'antd';

type Props = {
    minimal?: boolean;
};

export default function PageLoading({ minimal }: Props) {
    if (minimal) {
        return (
            <div className="flex">
                <Flex align="center" gap="middle">
                    <Spin indicator={<LoadingOutlined style={{ fontSize: 48 }} spin />} />
                </Flex>
            </div>
        );
    }

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
