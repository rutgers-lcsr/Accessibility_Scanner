"use client"

import { useEffect, useRef } from "react";

type Props = {
  url: string
  script?: string
}

function SiteIframe({ url, script }: Props) {
    const iframeRef = useRef<HTMLIFrameElement | null>(null);


    useEffect(() => {
        if (iframeRef.current) {
            const handleLoad = () => {
                const iframe = iframeRef.current;
                if (!iframe) return;
                const doc = iframe?.contentDocument || iframe.contentWindow?.document;

                if (doc) {
                    const accessScriptElement = doc.createElement("script");
                    accessScriptElement.src = "https://localhost:3000/api/reports/1/script/";
                    doc.body.appendChild(accessScriptElement);
                }
                };

            iframeRef.current.addEventListener("load", handleLoad);
            return () => {
                iframeRef.current?.removeEventListener("load", handleLoad);
            };
        }
    }, [url, script]);

  return (
    <div>
      <iframe ref={iframeRef} src={url} title="Website Preview" className="h-96 w-full rounded-lg border" security="restricted"/>
    </div>
  )
}

export default SiteIframe