'use client';
import ScanStatusTag from '@/components/ScanStatusTag';
import { IMPACTS } from '@/lib/impact';
import { Change, Owner, OwnerWebsite } from '@/lib/types/owners';
import { ArrowDownOutlined, ArrowUpOutlined } from '@ant-design/icons';
import { CheckboxProps, Table, TableColumnType, Tag, Typography } from 'antd';
import { formatDate } from 'date-fns';
import Link from 'next/link';
import { Key } from 'react';

// One table for owners and their websites: an owner row carries its websites as tree
// children, so a single header serves every cell, sorting reaches into each owner, and
// ticking an owner ticks all of its websites.
type Row = Owner | OwnerWebsite;
const isOwner = (row: Row): row is Owner => 'websites' in row;

type Props = {
    owners: Owner[];
    periodDays: number;
    selectedRowKeys: Key[];
    onSelectionChange: (keys: Key[]) => void;
};

// CheckboxProps has no aria attributes; antd passes these through to the <input>.
type LabelledCheckboxProps = CheckboxProps & { 'aria-label': string };

const numberSorter = (pick: (row: Row) => number) => (a: Row, b: Row) => pick(a) - pick(b);
const dateSorter = (pick: (row: Row) => string | null) => (a: Row, b: Row) =>
    (pick(a) ?? '').localeCompare(pick(b) ?? '');
const delta = (change: Change) => (change ? change.current - change.previous : null);
const date = (value: string | null) => (value ? formatDate(new Date(value), 'MMM d, yyyy') : null);

const Empty = () => <span className="text-gray-400">—</span>;

// Down is good. The sign, the arrow and the before/after numbers all carry the meaning,
// so colour is never the only cue.
function DeltaCell({ change }: { change: Change }) {
    const value = delta(change);
    if (change === null || value === null) return <Empty />;
    const tone = value < 0 ? 'text-green-700' : value > 0 ? 'text-red-700' : 'text-gray-500';
    return (
        <>
            <span className={`font-medium ${tone}`}>
                {value < 0 && <ArrowDownOutlined aria-hidden />}
                {value > 0 && <ArrowUpOutlined aria-hidden />} {value > 0 ? `+${value}` : value}
            </span>
            <div className="text-xs text-gray-500">
                {change.previous} → {change.current}
            </div>
        </>
    );
}

function Identity({ row }: { row: Row }) {
    if (isOwner(row)) {
        return (
            <>
                <strong>{row.username ?? 'Unassigned'}</strong>
                {row.email && (
                    <div className="text-xs">
                        <a href={`mailto:${row.email}`}>{row.email}</a>
                    </div>
                )}
            </>
        );
    }
    return (
        <>
            <Link href={`/websites/${row.id}`}>{row.url}</Link>
            {row.description && (
                <Typography.Paragraph
                    type="secondary"
                    style={{ marginBottom: 0, fontSize: 12 }}
                    ellipsis={{ rows: 1, expandable: 'collapsible' }}
                >
                    {row.description}
                </Typography.Paragraph>
            )}
            {(row.categories.length > 0 || row.users.length > 0) && (
                <div className="text-xs text-gray-500">
                    {row.categories.map((category) => (
                        <Tag key={category}>{category}</Tag>
                    ))}
                    {row.users.length > 0 && <span>with {row.users.join(', ')}</span>}
                </div>
            )}
        </>
    );
}

function OwnersTable({ owners, periodDays, selectedRowKeys, onSelectionChange }: Props) {
    const columns: TableColumnType<Row>[] = [
        {
            title: 'Owner / website',
            key: 'identity',
            width: 340,
            render: (_, row) => <Identity row={row} />,
            sorter: (a, b) =>
                (isOwner(a) ? (a.username ?? '') : a.url).localeCompare(
                    isOwner(b) ? (b.username ?? '') : b.url
                ),
        },
        {
            title: 'Websites',
            key: 'websites',
            align: 'right',
            render: (_, row) => (isOwner(row) ? row.websites_count : null),
            sorter: numberSorter((r) => (isOwner(r) ? r.websites_count : 0)),
        },
        {
            title: 'Pages',
            key: 'pages',
            align: 'right',
            render: (_, row) => `${row.pages_audited} / ${row.pages}`,
            sorter: numberSorter((r) => r.pages),
        },
        ...IMPACTS.map<TableColumnType<Row>>((impact) => ({
            title: impact.label,
            key: impact.key,
            align: 'right',
            render: (_, row) => row.violations[impact.key],
            sorter: numberSorter((r) => r.violations[impact.key]),
        })),
        {
            title: 'Total',
            key: 'total',
            align: 'right',
            render: (_, row) => <strong>{row.violations.total}</strong>,
            sorter: numberSorter((r) => r.violations.total),
            defaultSortOrder: 'descend',
        },
        {
            title: 'Last scanned',
            key: 'last_scanned',
            render: (_, row) => (
                <>
                    {date(row.last_scanned) ?? 'Never'}
                    {!isOwner(row) && (
                        <div>
                            <ScanStatusTag
                                status={row.last_scan_status}
                                lastScanned={row.last_scanned}
                            />
                        </div>
                    )}
                </>
            ),
            sorter: dateSorter((r) => r.last_scanned),
        },
        {
            title: 'Last emailed',
            key: 'last_notified',
            render: (_, row) => date(row.last_notified) ?? <Empty />,
            sorter: dateSorter((r) => r.last_notified),
        },
        {
            title: 'Last triage',
            key: 'last_triage',
            render: (_, row) => (
                <>
                    {date(row.activity.last_triage) ?? <Empty />}
                    {row.activity.triaged > 0 && (
                        <div className="text-xs text-gray-500">
                            {row.activity.triaged} finding{row.activity.triaged === 1 ? '' : 's'}
                        </div>
                    )}
                </>
            ),
            sorter: dateSorter((r) => r.activity.last_triage),
        },
        {
            title: 'Since last email',
            key: 'since_last_email',
            render: (_, row) => <DeltaCell change={row.since_last_email} />,
            sorter: numberSorter((r) => delta(r.since_last_email) ?? Number.MIN_SAFE_INTEGER),
        },
        {
            title: `Last ${periodDays} days`,
            key: 'since_period',
            render: (_, row) => <DeltaCell change={row.since_period} />,
            sorter: numberSorter((r) => delta(r.since_period) ?? Number.MIN_SAFE_INTEGER),
        },
    ];

    return (
        <Table<Row>
            rowKey={(row) => (isOwner(row) ? `owner:${row.username ?? ''}` : row.id)}
            columns={columns}
            dataSource={owners}
            expandable={{ childrenColumnName: 'websites' }}
            rowSelection={{
                selectedRowKeys,
                onChange: (keys) => onSelectionChange(keys),
                checkStrictly: false,
                getCheckboxProps: (row): LabelledCheckboxProps => ({
                    'aria-label': isOwner(row)
                        ? `Select all websites of ${row.username ?? 'unassigned'}`
                        : `Select ${row.url}`,
                }),
            }}
            pagination={{ pageSize: 20, hideOnSinglePage: true }}
            scroll={{ x: true }}
            size="middle"
            locale={{ emptyText: 'No websites found' }}
        />
    );
}

export default OwnersTable;
