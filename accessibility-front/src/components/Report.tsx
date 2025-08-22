"use client"
import { fetcherApi } from '@/lib/api';
import React from 'react'
import useSWR from 'swr';
import { Report as ReportType } from '@/lib/types/axe';
import PageLoading from './PageLoading';
import { Content } from 'antd/es/layout/layout';
type Props = {
    report_id: string;
}
import { AlertOutlined, ExclamationCircleOutlined, InfoCircleOutlined, WarningOutlined } from "@ant-design/icons";
import Console from './Console';

function Report({ report_id }: Props) {

    const { data: reportData, error, isLoading, } = useSWR(`/api/reports/${report_id}`, fetcherApi<ReportType>);

    if (isLoading) return <PageLoading />;
    if (error) return <div>Error loading report</div>;
    if (!reportData) return <div>No report data found</div>;

    const violations = reportData.report_counts.violations;

    return (
        <Content className="">
            <header className="mb-8">
                <h1 className="text-3xl font-extrabold mb-2">
                    Report for <span onClick={() => window.open(reportData.base_url)} className="underline text-blue-700">{reportData.base_url}</span>
                </h1>
                <h2 className="text-gray-500 text-lg mb-2">
                    Report Date: {reportData?.timestamp ? new Date(reportData.timestamp).toLocaleDateString() : 'N/A'}
                </h2>
                <h3 className="text-gray-500 text-lg mb-4">
                    Website: {reportData.base_url}
                </h3>
                <section
                    role="region"
                    aria-labelledby="accessibility-report"
                    className="bg-gray-50 rounded-lg p-6"
                >
                    <h2 id="accessibility-report" className="text-2xl font-semibold mb-6 text-gray-800">
                        Accessibility Report
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
                        <div className="bg-red-50 rounded-lg p-4 shadow-sm flex flex-col items-center">
                            <ExclamationCircleOutlined className="text-3xl text-red-700 mb-2" />
                            <h3 className="text-lg font-medium text-red-700 mb-2">Critical</h3>
                            <p className="text-3xl font-bold text-red-600">{violations.critical}</p>
                        </div>
                        <div className="bg-red-100 rounded-lg p-4 shadow-sm flex flex-col items-center">
                            <AlertOutlined className="text-3xl text-red-700 mb-2" />
                            <h3 className="text-lg font-medium text-red-700 mb-2">Serious</h3>
                            <p className="text-3xl font-bold text-red-600">{violations.serious}</p>
                        </div>
                        <div className="bg-orange-50 rounded-lg p-4 shadow-sm flex flex-col items-center">
                            <WarningOutlined className="text-3xl text-orange-700 mb-2" />
                            <h3 className="text-lg font-medium text-orange-700 mb-2">Moderate</h3>
                            <p className="text-3xl font-bold text-orange-600">{violations.moderate}</p>
                        </div>
                        <div className="bg-yellow-50 rounded-lg p-4 shadow-sm flex flex-col items-center">
                            <InfoCircleOutlined className="text-3xl text-yellow-700 mb-2" />
                            <h3 className="text-lg font-medium text-yellow-700 mb-2">Minor</h3>
                            <p className="text-3xl font-bold text-yellow-600">{violations.minor}</p>
                        </div>
                    </div>
                </section>
            </header>
            <Content>
                <div><Console command={`var accessScript = fetch('https://localhost:5000/api/reports/${report_id}/script');`} /></div>
            </Content>

            <pre>{JSON.stringify(reportData, null, 2)}</pre>
        </Content>
    )
}

export default Report