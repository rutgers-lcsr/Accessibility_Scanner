import { Card } from "antd";
import Link from "antd/es/typography/Link";

type Resources = {
  title: string;
    description: string;
    link: string;
};

function ResourceCard({ title, description, link }: Resources) {
    return (
        <Card title={<Link href={link} target="_blank" rel="noopener noreferrer">{title}</Link>}>
            <p>{description}</p>
        </Card>
    );
}

export default ResourceCard;