'use client';
import ExceptionsTable from '@/components/ExceptionsTable';
import PageLoading from '@/components/PageLoading';
import {
    ChecklistItem,
    ComplianceException,
    EXCEPTION_KIND_LABELS,
    ExceptionKind,
    ManualReview,
    REVIEW_RESULT_LABELS,
    ReviewEntry,
    ReviewResult,
} from '@/lib/types/compliance';
import { PublicUser } from '@/lib/types/user';
import { Website } from '@/lib/types/website';
import { useAlerts } from '@/providers/Alerts';
import { useUser } from '@/providers/User';
import {
    Alert,
    Button,
    Collapse,
    Descriptions,
    Input,
    Modal,
    Radio,
    Select,
    Table,
    Tag,
} from 'antd';
import { useState } from 'react';
import useSWR from 'swr';
import { Field } from './PanelFields';

type Props = {
    website: Website;
    user: PublicUser;
    canEdit: boolean;
    onChanged: () => void;
};

type ExceptionDraft = { kind: ExceptionKind; reason: string; rule_id: string; url_prefix: string };
type ReviewDraft = {
    id?: number;
    pages: string[];
    summary: string;
    results: Record<string, ReviewEntry>;
};

const RESULT_COLORS: Record<ReviewResult, string> = {
    pass: 'green',
    fail: 'red',
    not_applicable: 'default',
    not_tested: 'orange',
};

function Section({
    id,
    title,
    children,
}: {
    id: string;
    title: string;
    children: React.ReactNode;
}) {
    return (
        <section className="mb-10" aria-labelledby={id}>
            <h3
                id={id}
                style={{ marginBottom: 12 }}
                className="text-lg font-semibold text-gray-800"
            >
                {title}
            </h3>
            {children}
        </section>
    );
}

// Deadlines, the website's exceptions and its manual reviews.
function WebsiteCompliance({ website, user, canEdit, onChanged }: Props) {
    const { handlerUserApiRequest } = useUser();
    const { addAlert } = useAlerts();
    const base = `/api/websites/${website.id}`;
    const { data: exceptions, mutate: mutateExceptions } = useSWR(
        `${base}/exceptions/`,
        handlerUserApiRequest<ComplianceException[]>
    );
    const { data: reviews, mutate: mutateReviews } = useSWR(
        `${base}/reviews/`,
        handlerUserApiRequest<ManualReview[]>
    );
    const { data: checklist } = useSWR(
        '/api/reviews/checklist/',
        handlerUserApiRequest<ChecklistItem[]>
    );
    const [exceptionDraft, setExceptionDraft] = useState<ExceptionDraft | null>(null);
    const [reviewDraft, setReviewDraft] = useState<ReviewDraft | null>(null);
    const [prompt, setPrompt] = useState<string | null>(null);
    const [saving, setSaving] = useState(false);
    const c = website.compliance;

    const send = async (url: string, method: string, body: unknown) =>
        handlerUserApiRequest(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body),
        });

    const saveException = async () => {
        if (!exceptionDraft) return;
        setSaving(true);
        try {
            await send(`${base}/exceptions/`, 'POST', exceptionDraft);
            setExceptionDraft(null);
            await mutateExceptions();
            onChanged();
            addAlert(
                user.is_admin
                    ? 'Exception recorded'
                    : 'Exception requested; a site admin will review it',
                'success'
            );
        } catch (e) {
            addAlert('Could not save: ' + (e as Error).message, 'error');
        }
        setSaving(false);
    };

    const saveReview = async (status: 'in_progress' | 'completed') => {
        if (!reviewDraft) return;
        setSaving(true);
        try {
            const { id, ...body } = reviewDraft;
            await send(id ? `${base}/reviews/${id}/` : `${base}/reviews/`, id ? 'PATCH' : 'POST', {
                ...body,
                status,
            });
            setReviewDraft(null);
            await mutateReviews();
            onChanged();
        } catch (e) {
            addAlert('Could not save: ' + (e as Error).message, 'error');
        }
        setSaving(false);
    };

    const openPrompt = async () => {
        try {
            const data = await handlerUserApiRequest<{ prompt: string }>(`${base}/reviews/prompt/`);
            setPrompt(data.prompt);
        } catch (e) {
            addAlert('Could not build the prompt: ' + (e as Error).message, 'error');
        }
    };

    const setResult = (key: string, patch: Partial<ReviewEntry>) => {
        if (!reviewDraft) return;
        const current = reviewDraft.results[key] ?? {
            result: 'not_tested',
            notes: null,
            pages: [],
        };
        setReviewDraft({
            ...reviewDraft,
            results: { ...reviewDraft.results, [key]: { ...current, ...patch } },
        });
    };

    return (
        <div className="py-4">
            <Section id="deadlines" title="Deadlines">
                <Descriptions
                    size="small"
                    bordered
                    column={{ xs: 1, sm: 2, lg: 4 }}
                    items={[
                        {
                            key: 'overdue',
                            label: 'Overdue issues',
                            children: c.overdue ? <Tag color="red">{c.overdue}</Tag> : '0',
                        },
                        { key: 'soon', label: 'Due in the next 2 weeks', children: c.due_soon },
                        { key: 'excepted', label: 'Covered by an exception', children: c.excepted },
                        {
                            key: 'review',
                            label: 'Last manual review',
                            children: (
                                <>
                                    {c.last_review
                                        ? new Date(c.last_review).toLocaleDateString()
                                        : 'Never'}
                                    {c.review_due && (
                                        <>
                                            {' '}
                                            <Tag color="orange">
                                                {c.last_review ? 'Due again' : 'Due now'}
                                            </Tag>
                                        </>
                                    )}
                                </>
                            ),
                        },
                    ]}
                />
                <p style={{ marginTop: 8 }} className="text-xs text-gray-600">
                    Each open issue is due a set number of days after it was first found, by impact.
                    The Fix first tab shows the deadlines per rule.
                </p>
            </Section>

            <Section id="exceptions" title="Exceptions">
                <p style={{ marginBottom: 12 }} className="text-sm text-gray-600">
                    When content cannot be fixed by its deadline (archived pages, third-party
                    content, undue burden), record why. An approved exception stops the deadline for
                    the issues it covers until it expires; the issues still count.
                </p>
                {canEdit && (
                    <Button
                        className="mb-3"
                        onClick={() =>
                            setExceptionDraft({
                                kind: 'archived',
                                reason: '',
                                rule_id: '',
                                url_prefix: '',
                            })
                        }
                    >
                        {user.is_admin ? 'Record an exception' : 'Request an exception'}
                    </Button>
                )}
                {!exceptions ? (
                    <PageLoading minimal />
                ) : (
                    <ExceptionsTable
                        exceptions={exceptions}
                        isAdmin={user.is_admin}
                        canEdit={canEdit}
                        onChanged={() => {
                            mutateExceptions();
                            onChanged();
                        }}
                    />
                )}
            </Section>

            <Section id="reviews" title="Manual reviews">
                <p style={{ marginBottom: 12 }} className="text-sm text-gray-600">
                    Automated checks find only part of the accessibility problems on a page. A
                    manual review checks the rest: keyboard use, focus, screen readers, zoom,
                    captions and forms. Record one here, or hand the prompt to an agent that can
                    drive a browser; it submits its results with an API key.
                </p>
                {canEdit && (
                    <div className="mb-3 flex flex-wrap gap-2">
                        <Button
                            type="primary"
                            onClick={() =>
                                setReviewDraft({ pages: [website.url], summary: '', results: {} })
                            }
                        >
                            Start a review
                        </Button>
                        <Button onClick={openPrompt}>Prompt for an agent</Button>
                    </div>
                )}
                <Table<ManualReview>
                    rowKey="id"
                    loading={!reviews}
                    dataSource={reviews ?? []}
                    pagination={{ pageSize: 10, hideOnSinglePage: true }}
                    locale={{ emptyText: 'No manual reviews yet.' }}
                    expandable={{
                        expandedRowRender: (review) => (
                            <div className="space-y-2">
                                {review.summary && (
                                    <p className="whitespace-pre-line">{review.summary}</p>
                                )}
                                <ul className="space-y-1">
                                    {(checklist ?? [])
                                        .filter((item) => review.results[item.key])
                                        .map((item) => {
                                            const entry = review.results[item.key];
                                            return (
                                                <li key={item.key}>
                                                    <Tag color={RESULT_COLORS[entry.result]}>
                                                        {REVIEW_RESULT_LABELS[entry.result]}
                                                    </Tag>
                                                    {item.title}
                                                    {entry.notes && (
                                                        <div className="ml-2 text-sm text-gray-600 whitespace-pre-line">
                                                            {entry.notes}
                                                        </div>
                                                    )}
                                                </li>
                                            );
                                        })}
                                </ul>
                            </div>
                        ),
                    }}
                    columns={[
                        {
                            title: 'Started',
                            dataIndex: 'started_at',
                            key: 'started',
                            render: (v: string) => new Date(v).toLocaleDateString(),
                        },
                        {
                            title: 'By',
                            key: 'by',
                            render: (_, r) => (
                                <>
                                    {r.reviewer ?? '—'}
                                    {r.source === 'agent' && (
                                        <Tag className="ml-2">
                                            agent{r.tool ? `: ${r.tool}` : ''}
                                        </Tag>
                                    )}
                                </>
                            ),
                        },
                        {
                            title: 'Status',
                            dataIndex: 'status',
                            key: 'status',
                            render: (s: ManualReview['status']) =>
                                s === 'completed' ? (
                                    <Tag color="green">Completed</Tag>
                                ) : (
                                    <Tag>In progress</Tag>
                                ),
                        },
                        {
                            title: 'Results',
                            key: 'counts',
                            render: (_, r) => (
                                <span className="flex flex-wrap gap-1">
                                    {(Object.keys(REVIEW_RESULT_LABELS) as ReviewResult[])
                                        .filter((k) => r.counts[k])
                                        .map((k) => (
                                            <Tag key={k} color={RESULT_COLORS[k]}>
                                                {r.counts[k]}{' '}
                                                {REVIEW_RESULT_LABELS[k].toLowerCase()}
                                            </Tag>
                                        ))}
                                </span>
                            ),
                        },
                        ...(canEdit
                            ? [
                                  {
                                      title: '',
                                      key: 'edit',
                                      render: (_: unknown, r: ManualReview) =>
                                          r.status === 'in_progress' && (
                                              <Button
                                                  size="small"
                                                  onClick={() =>
                                                      setReviewDraft({
                                                          id: r.id,
                                                          pages: r.pages,
                                                          summary: r.summary ?? '',
                                                          results: r.results,
                                                      })
                                                  }
                                              >
                                                  Continue
                                              </Button>
                                          ),
                                  },
                              ]
                            : []),
                    ]}
                />
            </Section>

            <Modal
                open={exceptionDraft !== null}
                title={user.is_admin ? 'Record an exception' : 'Request an exception'}
                okText={user.is_admin ? 'Record' : 'Request'}
                confirmLoading={saving}
                onOk={saveException}
                onCancel={() => setExceptionDraft(null)}
                width={640}
            >
                {exceptionDraft && (
                    <div className="space-y-4">
                        <Field id="exc-kind" label="Kind">
                            <Select<ExceptionKind>
                                id="exc-kind"
                                style={{ width: '100%' }}
                                value={exceptionDraft.kind}
                                onChange={(kind) => setExceptionDraft({ ...exceptionDraft, kind })}
                                options={(
                                    Object.keys(EXCEPTION_KIND_LABELS) as ExceptionKind[]
                                ).map((value) => ({
                                    value,
                                    label: EXCEPTION_KIND_LABELS[value],
                                }))}
                            />
                        </Field>
                        <Field
                            id="exc-reason"
                            label="Reason"
                            help="Why it cannot be fixed by its deadline, and what users can do instead (an alternative format, a contact)."
                        >
                            <Input.TextArea
                                id="exc-reason"
                                rows={4}
                                value={exceptionDraft.reason}
                                onChange={(e) =>
                                    setExceptionDraft({ ...exceptionDraft, reason: e.target.value })
                                }
                            />
                        </Field>
                        <Field
                            id="exc-rule"
                            label="Rule (optional)"
                            help="An axe rule id such as color-contrast. Leave empty for every rule."
                        >
                            <Input
                                id="exc-rule"
                                value={exceptionDraft.rule_id}
                                onChange={(e) =>
                                    setExceptionDraft({
                                        ...exceptionDraft,
                                        rule_id: e.target.value,
                                    })
                                }
                            />
                        </Field>
                        <Field
                            id="exc-prefix"
                            label="Pages (optional)"
                            help={`Pages whose address starts with this, e.g. ${website.url}/archive/. Leave empty for every page.`}
                        >
                            <Input
                                id="exc-prefix"
                                value={exceptionDraft.url_prefix}
                                onChange={(e) =>
                                    setExceptionDraft({
                                        ...exceptionDraft,
                                        url_prefix: e.target.value,
                                    })
                                }
                            />
                        </Field>
                        {!user.is_admin && (
                            <Alert
                                type="info"
                                showIcon
                                title="A site admin approves or rejects the request."
                            />
                        )}
                    </div>
                )}
            </Modal>

            <Modal
                open={reviewDraft !== null}
                title="Manual review"
                width={900}
                onCancel={() => setReviewDraft(null)}
                footer={[
                    <Button key="cancel" onClick={() => setReviewDraft(null)}>
                        Cancel
                    </Button>,
                    <Button key="save" loading={saving} onClick={() => saveReview('in_progress')}>
                        Save and finish later
                    </Button>,
                    <Button
                        key="done"
                        type="primary"
                        loading={saving}
                        onClick={() => saveReview('completed')}
                    >
                        Complete review
                    </Button>,
                ]}
            >
                {reviewDraft && (
                    <div className="space-y-4">
                        <Field id="review-pages" label="Pages tested">
                            <Select
                                id="review-pages"
                                mode="tags"
                                style={{ width: '100%' }}
                                value={reviewDraft.pages}
                                onChange={(pages: string[]) =>
                                    setReviewDraft({ ...reviewDraft, pages })
                                }
                            />
                        </Field>
                        <Collapse
                            items={(checklist ?? []).map((item) => {
                                const entry = reviewDraft.results[item.key];
                                return {
                                    key: item.key,
                                    label: (
                                        <span className="flex flex-wrap items-center gap-2">
                                            {entry && (
                                                <Tag color={RESULT_COLORS[entry.result]}>
                                                    {REVIEW_RESULT_LABELS[entry.result]}
                                                </Tag>
                                            )}
                                            {item.title}
                                            <span className="text-xs text-gray-600">
                                                WCAG {item.wcag}
                                            </span>
                                        </span>
                                    ),
                                    children: (
                                        <div className="space-y-3">
                                            <p className="text-sm text-gray-700">{item.how}</p>
                                            <Radio.Group
                                                aria-label={`Result for ${item.title}`}
                                                value={entry?.result}
                                                onChange={(e) =>
                                                    setResult(item.key, { result: e.target.value })
                                                }
                                                options={(
                                                    Object.keys(
                                                        REVIEW_RESULT_LABELS
                                                    ) as ReviewResult[]
                                                ).map((value) => ({
                                                    value,
                                                    label: REVIEW_RESULT_LABELS[value],
                                                }))}
                                            />
                                            <Input.TextArea
                                                aria-label={`Notes for ${item.title}`}
                                                placeholder="What you did, what happened, where"
                                                rows={2}
                                                value={entry?.notes ?? ''}
                                                disabled={!entry}
                                                onChange={(e) =>
                                                    setResult(item.key, { notes: e.target.value })
                                                }
                                            />
                                        </div>
                                    ),
                                };
                            })}
                        />
                        <Field id="review-summary" label="Summary">
                            <Input.TextArea
                                id="review-summary"
                                rows={3}
                                value={reviewDraft.summary}
                                onChange={(e) =>
                                    setReviewDraft({ ...reviewDraft, summary: e.target.value })
                                }
                            />
                        </Field>
                    </div>
                )}
            </Modal>

            <Modal
                open={prompt !== null}
                title="Prompt for an agent"
                width={900}
                onCancel={() => setPrompt(null)}
                footer={[
                    <Button
                        key="copy"
                        type="primary"
                        onClick={async () => {
                            try {
                                await navigator.clipboard.writeText(prompt ?? '');
                                addAlert('Prompt copied', 'success');
                            } catch {
                                addAlert(
                                    'Copy failed; select the text and copy it by hand',
                                    'error'
                                );
                            }
                        }}
                    >
                        Copy
                    </Button>,
                    <Button key="close" onClick={() => setPrompt(null)}>
                        Close
                    </Button>,
                ]}
            >
                <p style={{ marginBottom: 8 }} className="text-sm text-gray-600">
                    Give this to an agent that can drive a real browser, together with an API key
                    from Settings, API Keys (the key&apos;s owner must be able to edit this
                    website). The agent records its review here when it finishes.
                </p>
                <Input.TextArea
                    aria-label="Agent prompt"
                    readOnly
                    rows={18}
                    value={prompt ?? ''}
                    className="font-mono"
                />
            </Modal>
        </div>
    );
}

export default WebsiteCompliance;
