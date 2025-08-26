'use client';
import { Button } from 'antd';
import { useRouter } from 'next/navigation';
interface Props {
    url: string;
}

export default function HeaderLink({ url }: Props) {
    const router = useRouter();

    return (
        <Button
            type="link"
            size="large"
            onClick={() => router.push(url)}
            style={{
                color: 'inherit',
                fontSize: 'inherit',
                textWrap: 'wrap',
                padding: 0,
                margin: 0,
            }}
        >
            {url}
        </Button>
    );
}
