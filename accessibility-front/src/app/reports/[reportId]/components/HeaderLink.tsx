interface Props {
    url: string;
}

// The scanned address in a page title: a plain link to the live page, opening in a new
// tab (said for screen readers). It used to be a button whose job was invisible to them.
export default function HeaderLink({ url }: Props) {
    return (
        <a
            href={url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-inherit underline underline-offset-4"
            style={{
                color: 'inherit',
                // A long URL breaks across lines instead of widening the page on a phone.
                overflowWrap: 'anywhere',
            }}
        >
            {url.replace(/(^\w+:|^)\/\//, '')}
            <span className="sr-only"> (opens in a new tab)</span>
        </a>
    );
}
