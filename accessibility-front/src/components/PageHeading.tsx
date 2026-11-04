type Props = {
    title?: React.ReactNode;
    subtitle?: string;
    actions?: React.ReactNode;
};

// Title bar at the top of each page. Wraps rather than truncating, so a long title or the
// actions never push the page wider than a phone screen.
const PageHeading = (props: Props) => {
    return (
        <header className="mb-6 border-b border-[#e4e4e4] bg-white px-4 py-4 md:px-6 md:py-5">
            <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
                <div className="min-w-0 flex-1 basis-64">
                    {props.title && (
                        <h1
                            className="text-2xl leading-tight tracking-tight text-gray-900 md:text-[1.75rem]"
                            style={{ margin: 0, fontWeight: 600 }}
                        >
                            {props.title}
                        </h1>
                    )}
                    {props.subtitle && (
                        <p
                            className="mt-1 text-sm text-gray-600 md:text-base"
                            style={{ marginBottom: 0 }}
                        >
                            {props.subtitle}
                        </p>
                    )}
                </div>
                {props.actions && (
                    <div className="flex flex-wrap items-center gap-2">{props.actions}</div>
                )}
            </div>
        </header>
    );
};

export default PageHeading;
