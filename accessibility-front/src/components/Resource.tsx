import { ExportOutlined } from '@ant-design/icons';

type Resource = {
    title: string;
    description: string;
    link: string;
};

// One entry in the Home page's resource list. Off-site links open in a new tab and say so.
function ResourceLink({ title, description, link }: Resource) {
    const external = !link.startsWith('/');
    return (
        <li className="py-2.5">
            <a
                href={link}
                {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
                className="font-medium text-[#007fac] underline-offset-2 hover:text-[#005f80] hover:underline"
            >
                {title}
                {external && (
                    <>
                        <ExportOutlined aria-hidden="true" className="ml-1.5 text-xs" />
                        <span className="sr-only"> (opens in a new tab)</span>
                    </>
                )}
            </a>
            <p className="mt-0.5 text-sm text-gray-600" style={{ marginBottom: 0 }}>
                {description}
            </p>
        </li>
    );
}

export default ResourceLink;
