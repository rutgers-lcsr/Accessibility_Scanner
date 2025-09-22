'use client';

type Props = {
    url: string;
};

function SiteIframe({ url }: Props) {
    console.log('Rendering iframe for URL:', url);
    return (
        <iframe
            tabIndex={-1}
            onError={(e) => console.error('Iframe error:', e)}
            // onLoad={handleLoad}
            // ref={iframeRef}
            src={url}
            title="Website Preview"
            className="w-full min-h-[700px]"
            style={{ border: 'none' }}
            sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-modals"
            allow="geolocation; microphone; camera; midi; vr; accelerometer; gyroscope; payment; ambient-light-sensor; autoplay; clipboard-read; clipboard-write"
        />
    );
}

export default SiteIframe;
