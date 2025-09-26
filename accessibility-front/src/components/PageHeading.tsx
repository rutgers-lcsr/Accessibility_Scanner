import { Flex } from 'antd';
import { Header } from 'antd/es/layout/layout';

type Props = {
    title?: string;
    subtitle?: string;
    actions?: React.ReactNode;
};

const PageHeading = (props: Props) => {
    return (
        <Header
            className="shadow-sm"
            style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'left',
                padding: '16px',
                marginBottom: 24,
                minHeight: 75,
            }}
            title={props.title}
        >
            <Flex
                gap={10}
                style={{
                    flexGrow: 1,
                    justifyContent: 'flex-start',
                    alignItems: 'center',
                    paddingTop: 10,
                }}
            >
                <div className="mr-4">
                    {props.title && (
                        <h1 className="text-2xl md:text-3xl font-semibold text-gray-900 truncate line-clamp-1">
                            {props.title}
                        </h1>
                    )}
                </div>
                <div className="mt-2">
                    {props.subtitle && (
                        <p className="text-gray-500 text-base md:text-lg truncate">
                            {props.subtitle}
                        </p>
                    )}
                </div>
            </Flex>
            {props.actions && (
                <div className="flex flex-row gap-2 mt-4 md:mt-0 flex-shrink-0 mr-4">
                    {props.actions}
                </div>
            )}
        </Header>
    );
};

export default PageHeading;
