type Props = {
    status?: number;
    title?: string;
    subTitle?: string;
    details?: string;
    link?: string;
    linkName?: string;
};

function ProxyError({ status, title, subTitle, details, link, linkName }: Props) {
    return (
        <html>
            <body>
                <title>{title || 'Proxy Error'}</title>
                <meta name="viewport" content="width=device-width, initial-scale=1" />
                <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4" async></script>
                <div className="flex flex-col items-center justify-center min-h-screen py-6 bg-gray-100">
                    <h1 className="text-4xl font-bold text-red-600">{title || 'Proxy Error'}</h1>
                    <p className="mt-2 text-lg text-gray-600">
                        {subTitle || 'An error occurred while fetching the requested resource.'}
                    </p>
                    {status && (
                        <span className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded">
                            Status code: {status}
                        </span>
                    )}
                    {details && (
                        <div className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded">
                            {details}
                        </div>
                    )}
                    {link && (
                        <a
                            href={link}
                            className="mt-6 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                        >
                            {linkName || 'Learn More'}
                        </a>
                    )}
                </div>
            </body>
        </html>
    );
}

export default ProxyError;
