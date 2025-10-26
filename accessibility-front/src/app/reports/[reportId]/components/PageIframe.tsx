'use client';

type Props = {
    url: string;
};

function PageIframe({ url }: Props) {
    return (
        <iframe
            tabIndex={0}
            onError={(e) => console.error('Iframe error:', e)}
            // onLoad={handleLoad}
            // ref={iframeRef}
            src={url}
            title="Page Preview"
            className="w-full min-h-[700px]"
            style={{ border: 'none' }}
            allow="*"
        />
    );
}

export default PageIframe;
