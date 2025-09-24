'use client';

type Props = {
    url: string;
};

function PageIframe({ url }: Props) {
    console.log('Rendering iframe for URL:', url);
    return (
        <iframe
            tabIndex={-1}
            onError={(e) => console.error('Iframe error:', e)}
            // onLoad={handleLoad}
            // ref={iframeRef}
            src={url}
            title="Page Preview"
            className="w-full min-h-[700px]"
            style={{ border: 'none' }}
            sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-modals"
            allow="clipboard-read; clipboard-write"
        />
    );
}

export default PageIframe;
