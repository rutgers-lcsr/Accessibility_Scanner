import React from 'react'

type Props = {
    report_id: string;
}

function Report({ report_id }: Props) {
    return (
        <div>Report {report_id}</div>
    )
}

export default Report