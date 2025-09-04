'use client';
import { Button } from 'antd';
interface Props {
    url: string;
}

export default function HeaderLink({ url }: Props) {

    const openLink = () => {
        window.open(url, '_blank');
    };

    return (
        <Button
            type="link"
            size="large"
            onAuxClick={openLink}
            onClick={openLink}
            style={{
                color: 'inherit',
                fontSize: 'inherit',
                textWrap: 'wrap',
                padding: 0,
                margin: 0,
                textDecoration: 'underline',
                transition: 'color 0.3s',
                

            }}
        >
            {url.replace(/(^\w+:|^)\/\//, '')}
        </Button>
    );
}
