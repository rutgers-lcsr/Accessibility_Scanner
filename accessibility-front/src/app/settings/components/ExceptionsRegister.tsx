'use client';
import ExceptionsTable from '@/components/ExceptionsTable';
import PageLoading from '@/components/PageLoading';
import { ComplianceException, ExceptionStatus } from '@/lib/types/compliance';
import { useUser } from '@/providers/User';
import { Select } from 'antd';
import { useState } from 'react';
import useSWR from 'swr';

// Every website's exceptions in one place for site admins: requests waiting for a
// decision first.
function ExceptionsRegister() {
    const { handlerUserApiRequest } = useUser();
    const [status, setStatus] = useState<ExceptionStatus | 'all'>('all');
    const { data, mutate } = useSWR(
        `/api/exceptions/${status === 'all' ? '' : `?status=${status}`}`,
        handlerUserApiRequest<ComplianceException[]>
    );
    return (
        <div className="max-w-6xl">
            <p className="mb-4 text-sm text-gray-600">
                Exceptions document why content will not meet its deadline. Approve them with an
                expiry date so they are reconsidered; expired ones no longer stop deadlines.
            </p>
            <div className="mb-3 flex items-center gap-2">
                <label htmlFor="exceptions-status">Show</label>
                <Select<ExceptionStatus | 'all'>
                    id="exceptions-status"
                    style={{ width: 200 }}
                    value={status}
                    onChange={setStatus}
                    options={[
                        { value: 'all', label: 'All' },
                        { value: 'requested', label: 'Waiting for a decision' },
                        { value: 'approved', label: 'Approved' },
                        { value: 'expired', label: 'Expired' },
                        { value: 'rejected', label: 'Rejected' },
                    ]}
                />
            </div>
            {!data ? (
                <PageLoading minimal />
            ) : (
                <ExceptionsTable
                    exceptions={data}
                    isAdmin
                    canEdit
                    showWebsite
                    onChanged={() => mutate()}
                />
            )}
        </div>
    );
}

export default ExceptionsRegister;
