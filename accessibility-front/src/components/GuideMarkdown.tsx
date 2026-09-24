'use client';
import 'highlight.js/styles/github.css';
import '@/styles/guide.css';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';

// A guide section. Raw HTML in the markdown stays escaped, which is what a guide full
// of <div> examples needs; links open in a new tab.
function GuideMarkdown({ markdown }: { markdown: string }) {
    return (
        <div className="guide-markdown">
            <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                rehypePlugins={[rehypeHighlight]}
                components={{
                    a: ({ href, children }) => (
                        <a href={href} target="_blank" rel="noopener noreferrer">
                            {children}
                        </a>
                    ),
                }}
            >
                {markdown}
            </ReactMarkdown>
        </div>
    );
}

export default GuideMarkdown;
