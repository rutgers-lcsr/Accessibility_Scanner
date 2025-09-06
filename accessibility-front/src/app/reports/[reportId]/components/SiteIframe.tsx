'use client';

type Props = {
    url: string;
};

function SiteIframe({ url }: Props) {
    // const iframeRef = useRef<HTMLIFrameElement>(null);

    // useEffect(() => {}, []);
    // const handleLoad = (e: React.SyntheticEvent<HTMLIFrameElement>) => {
    //     const iframe = e.target as HTMLIFrameElement;
    //     console.log('Iframe loaded:', iframe);
    //     try {
    //         console.log(iframe.contentWindow);
    //     } catch (error) {
    //         console.error('Error occurred while loading iframe:', error);
    //     }
    // };

    return (
        <iframe
            tabIndex={-1}
            onError={(e) => console.error('Iframe error:', e)}
            // onLoad={handleLoad}
            // ref={iframeRef}
            src={url}
            title="Website Preview"
            className="w-full min-h-[700px]"
        />
    );
}

export default SiteIframe;
