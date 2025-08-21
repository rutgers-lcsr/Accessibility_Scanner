import React from 'react'

type Props = {
    websiteId: number;
}

const Website = ({ websiteId }: Props) => {
    return (
        <div>Website ID: {websiteId}</div>
    )
}

export default Website