"use client"

import { useEffect, useRef } from "react";


type Props = {
  url: string
}

function SiteIframe({ url }: Props) {

  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Check Ctrl + Shift + K
      if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "k") {
        iframeRef.current?.childNodes.forEach((node) => {
          if (node instanceof HTMLElement) {
            node.focus();
          }
        });
        iframeRef.current?.contentWindow?.focus();
        iframeRef.current?.style.setProperty("outline", "2px solid blue");
        console.log("Ctrl + Shift + K pressed");
        console.log(iframeRef.current);

      }
      console.log(event.ctrlKey, event.shiftKey, event.key);
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <div>
       <iframe tabIndex={-1} ref={iframeRef} src={url} title="Website Preview" className="w-full min-h-[500px]"/>
    </div>
  )
}

export default SiteIframe