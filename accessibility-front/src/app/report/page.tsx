'use client';
import React from 'react';
import { Table, Typography } from 'antd';

const { Title } = Typography;

const reports = [
    { id: 1, title: 'Accessibility Audit Q1', date: '2024-03-15', status: 'Completed' },
    { id: 2, title: 'Accessibility Audit Q2', date: '2024-06-10', status: 'In Progress' },
    { id: 3, title: 'Accessibility Audit Q3', date: '2024-09-05', status: 'Scheduled' },
];

const columns = [
    {
        title: 'Title',
        dataIndex: 'title',
        key: 'title',
    },
    {
        title: 'Date',
        dataIndex: 'date',
        key: 'date',
    },
    {
        title: 'Status',
        dataIndex: 'status',
        key: 'status',
    },
];

export default function ReportPage() {
    return (
        <main style={{ padding: 24 }}>
            <Title level={2}>Accessibility Reports</Title>
            <Table
                dataSource={reports}
                columns={columns}
                rowKey="id"
                pagination={false}
            />
        </main>
    );
}