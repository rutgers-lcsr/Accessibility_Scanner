import { Flex, Spin } from "antd";
import { LoadingOutlined } from "@ant-design/icons";

export default function PageLoading() {
    return (
        <div className="flex items-center justify-center h-screen">
            <Flex align="center" gap="middle">
                <Spin tip="Loading..." indicator={<LoadingOutlined style={{ fontSize: 48 }} spin allowFullScreen />} />
            </Flex>
        </div>
    );
}
