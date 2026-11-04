import { HTMLAttributes } from 'react';

// Page body container. antd's Layout.Content renders a <main>, but the root layout already
// wraps every page in the one <main> landmark, so pages use this plain div instead.
function Content(props: HTMLAttributes<HTMLDivElement>) {
    return <div {...props} />;
}

export default Content;
