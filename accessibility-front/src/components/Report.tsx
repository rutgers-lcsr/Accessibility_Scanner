"use client"
import { fetcherApi } from '@/lib/api';
import React from 'react'
import useSWR from 'swr';
import { Report as ReportType } from '@/lib/types/axe';
import PageLoading from './PageLoading';
import { Content } from 'antd/es/layout/layout';
import { format } from 'date-fns';
import { useRouter } from 'next/navigation';
type Props = {
    report_id: string;
}
import { AlertOutlined, ExclamationCircleOutlined, InfoCircleOutlined, WarningOutlined } from "@ant-design/icons";
import Console from './Console';

import AuditAccessibilityItem from './AuditAccessibilityItem';
import { Image } from 'antd';
import { useUser } from '@/providers/User';
import AdminReportItems from './AdminReportItems';

function Report({ report_id }: Props) {

    const { is_admin } = useUser();
    const { data: reportData, error, isLoading, } = useSWR(`/api/reports/${report_id}`, fetcherApi<ReportType>);

    if (isLoading) return <PageLoading />;
    if (error) return <div>Error loading report</div>;
    if (!reportData) return <div>No report data found</div>;

    const violations = reportData.report_counts.violations;

    const report_script_full_url = process.env.NODE_ENV === "development" ? `http://localhost:5000/api/reports/${report_id}/script` : `${window.location.origin}/api/reports/${report_id}/script`;

    const report_photo_url = process.env.NODE_ENV === "development" ? `http://localhost:5000/api/reports/${report_id}/photo` : `${window.location.origin}/api/reports/${report_id}/photo`;

    return (
        <Content className="">
            <header className="mb-8">
                <h1 className="text-3xl font-extrabold mb-2">
                    Report for <span onClick={() => window.open(reportData.url)} className="underline text-blue-700 cursor-pointer">{reportData.url}</span>
                </h1>
                {is_admin && <AdminReportItems report={reportData} />}
                <h2 className="text-gray-500 text-lg mb-2">
                    Report Date: {reportData?.timestamp ? format(new Date(reportData.timestamp), 'MMMM dd, yyyy') : 'N/A'}
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
            <Content className="mb-8">
                <div className="mb-4 max-h-[300px] overflow-auto">
                    <Image
                        src={report_photo_url}
                        alt="Report Photo"

                        className="rounded-lg"
                    />
                </div>

                <div>
                    <h2 className="text-2xl font-semibold mb-4">Inject Script</h2>
                    <p className="mb-2">To view the accessibility issues directly on the webpage, inject the following script into the browser console while on the page you want to audit:</p>
                </div>
                <Console label="Accessibility Report Script" command={`var accessScriptElement = document.createElement('script');
accessScriptElement.src = '${report_script_full_url}';
document.body.appendChild(accessScriptElement);
                `} />

                <div className="mt-8">
                    <div>
                        <h2 className="text-2xl font-semibold mb-4">Accessibility Issues</h2>
                        <p className="mb-2">The following accessibility issues were found on the page:</p>
                    </div>
                    <div className="mt-4">
                        {reportData.report.violations.map((violation, index) => (
                            <AuditAccessibilityItem key={index} accessibilityResult={violation} />
                        ))}
                    </div>
                </div>

            </Content>

            {/* <pre>{JSON.stringify(reportData, null, 2)}</pre> */}
        </Content>
    )
}

export default Report