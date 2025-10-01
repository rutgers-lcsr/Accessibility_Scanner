'use client';
import { Button } from 'antd';
interface Props {
    url: string;
}

export default function HeaderLink({ url }: Props) {
    const openLink = (e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        window.open(url, '_blank');
    };

    return (
        <Button
            type="link"
            size="large"
            onAuxClick={openLink}
            onClick={openLink}
            onMouseDown={openLink}
            style={{
                color: 'inherit',
                fontSize: 'inherit',
                textWrap: 'wrap',
                padding: 0,
                margin: 0,
                textDecoration: 'underline',
                transition: 'color 0.3s',
                userSelect: 'all',
            }}
        >
            {url.replace(/(^\w+:|^)\/\//, '')}
        </Button>
    );
}
