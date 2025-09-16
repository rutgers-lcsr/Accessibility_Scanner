'use client';
import EditableCode from '@/components/EditableCode';
import EditableInput from '@/components/EditableInput';
import PageLoading from '@/components/PageLoading';
import { Check, Rule, RulesChecks } from '@/lib/types/axe';
import { useRules } from '@/providers/Rules';
import { InfoCircleOutlined, PlusOutlined } from '@ant-design/icons';
import { DragDropContext, Draggable, Droppable } from '@hello-pangea/dnd';
import { Button, Card, Flex, Select, Space, Switch } from 'antd';
import { useState } from 'react';
import AddCheck from './AddCheck';
import CheckComponent from './CheckComponent';

type Props = {
    rule: Rule;
};

export default function RuleComponent({ rule }: Props) {
    const { fetchChecks, updateRule, deleteRule, tags, exportRule } = useRules();
    const [collapsed, setCollapsed] = useState(true);
    const [loadingChecks, setLoadingChecks] = useState(false);
    const [checks, setChecks] = useState<RulesChecks>({ all: [], any: [], none: [] });
    const [checkModalOpen, setCheckModalOpen] = useState(false);

    const toggleCollapse = async (collapsed: boolean) => {
        if (!collapsed) {
            setLoadingChecks(true);
            // fetch checks only when expanding
            const checks = await fetchChecks(rule.id);
            setChecks(checks);
            setLoadingChecks(false);
        }

        setCollapsed(collapsed);
    };

    const updateRuleField = async <K extends keyof Rule>(field: K, value: Rule[K]) => {
        await updateRule(rule.id, { [field]: value });
    };

    const moveCheck = async (checkId: number, from: keyof RulesChecks, to: keyof RulesChecks) => {
        if (from === to) return; // No need to move if the same category
        if (!checks[from] || !checks[to]) return; // Invalid categories

        const toCheck = checks[from].find((check) => check.id === checkId);
        const fromChecks = checks[from].filter((check) => check.id !== checkId);
        if (!toCheck) return; // Check not found in the source category

        const toChecks = [...checks[to], toCheck];

        // Update state optimistically
        setChecks({
            ...checks,
            [from]: fromChecks,
            [to]: toChecks,
        });

        // Update the rule on the server
        const fromCheckIds = fromChecks.map((check) => check.id);
        const toCheckIds = toChecks.map((check) => check.id);

        await updateRule(rule.id, {
            [from]: fromCheckIds,
            [to]: toCheckIds,
        });
    };
    const updateCheckFunction = (checkType: keyof RulesChecks) => {
        return async function (updateCheck: Check, deleted?: boolean) {
            if (deleted) {
                const updatedChecks = checks[checkType].filter((chk) => chk.id !== updateCheck.id);
                setChecks({
                    ...checks,
                    [checkType]: updatedChecks,
                });
                return;
            }

            const updatedChecks = checks[checkType].map((chk) =>
                chk.id === updateCheck.id ? updateCheck : chk
            );
            setChecks({
                ...checks,
                [checkType]: updatedChecks,
            });
        };
    };

    return (
        <Card
            title={rule.name}
            extra={
                <span className="flex gap-2 items-center">
                    <Switch
                        className="z-11"
                        title={rule.enabled ? 'Disable Rule' : 'Enable Rule'}
                        checked={rule.enabled}
                        onChange={(checked) => updateRuleField('enabled', checked)}
                    />
                </span>
            }
            style={{ width: '100%' }}
        >
            {!rule.enabled && (
                <div className="w-full absolute inset-0 bg-gray-100 opacity-50 z-10" />
            )}
            {collapsed ? (
                <Space
                    className={rule.enabled ? 'w-full relative' : 'w-full opacity-50'}
                    direction="vertical"
                    size="large"
                >
                    <EditableInput
                        label="Description"
                        value={rule.description}
                        onChange={(value) => updateRuleField('description', value)}
                    />
                    <EditableInput
                        label="Selector"
                        value={rule.selector}
                        onChange={(value) => updateRuleField('selector', value)}
                        validate={(value) => {
                            try {
                                document.createDocumentFragment().querySelector(value);
                                return null;
                            } catch {
                                return 'Invalid CSS selector';
                            }
                        }}
                    />
                    <EditableCode
                        label="Match Function"
                        value={rule.matches || ''}
                        onChange={(value) => updateRuleField('matches', value)}
                    />
                    <EditableInput
                        label="Help Text"
                        value={rule.help}
                        onChange={(value) => updateRuleField('help', value)}
                    />
                    <EditableInput
                        label="Help URL"
                        value={rule.help_url || ''}
                        type="url"
                        validate={(value) => {
                            return value && !/^https?:\/\/[^\s$.?#].[^\s]*$/.test(value)
                                ? 'Invalid URL'
                                : null;
                        }}
                        onChange={(value) => updateRuleField('help_url', value)}
                    />
                    <Select
                        mode="tags"
                        style={{ width: '100%' }}
                        value={rule.tags}
                        onChange={(value) => updateRuleField('tags', value)}
                    >
                        {rule.tags.map((tag) => (
                            <Select.Option key={tag} value={tag} label={<span>{tag}</span>}>
                                {tag}
                            </Select.Option>
                        ))}
                        {(tags &&
                            tags
                                .filter((tag) => !rule.tags.includes(tag))
                                .map((tag) => (
                                    <Select.Option key={tag} value={tag} label={<span>{tag}</span>}>
                                        {tag}
                                    </Select.Option>
                                ))) ||
                            null}
                    </Select>

                    <Select
                        style={{ width: '100%', marginTop: '10px' }}
                        value={rule.impact}
                        onChange={(value) => updateRuleField('impact', value)}
                    >
                        <Select.Option value="minor">Minor</Select.Option>
                        <Select.Option value="moderate">Moderate</Select.Option>
                        <Select.Option value="serious">Serious</Select.Option>
                        <Select.Option value="critical">Critical</Select.Option>
                    </Select>
                    <Flex gap={8} className="mb-4">
                        <label className="block mb-2 text-md">Exclude Hidden Elements</label>

                        <Switch
                            className="z-11"
                            title="Exclude Hidden Elements"
                            checked={rule.exclude_hidden}
                            onChange={(checked) => updateRuleField('exclude_hidden', checked)}
                        />
                        <span className="text-gray-500 text-sm mb-2">
                            If enabled, this rule will not check elements that are hidden from the
                            accessibility tree.
                        </span>
                    </Flex>

                    <Flex justify="space-between" align="center">
                        <Button onClick={() => toggleCollapse(false)}>View Checks</Button>
                        <Flex gap={8}>
                            <Button onClick={() => exportRule(rule.id)}>Export</Button>

                            <Button type="primary" onClick={() => deleteRule(rule.id)} danger>
                                Delete Rule
                            </Button>
                        </Flex>
                    </Flex>

                    {!rule.enabled && (
                        <div className="text-red-500 mb-2">This rule is disabled</div>
                    )}
                </Space>
            ) : (
                <div>
                    <h2 className="text-xl font-bold mb-4">Associated Checks</h2>
                    {loadingChecks && <PageLoading minimal />}
                    <div className={loadingChecks ? 'opacity-50 pointer-events-none' : 'mb-4'}>
                        <DragDropContext
                            onDragEnd={(result) => {
                                const { source, destination, draggableId } = result;
                                if (!destination) return;
                                const checkId = draggableId.replace(/^check-/, '');
                                const from = source.droppableId as keyof RulesChecks;
                                const to = destination.droppableId as keyof RulesChecks;
                                moveCheck(parseInt(checkId), from, to);
                            }}
                        >
                            <div className="flex gap-6 items-start">
                                {(['all', 'any', 'none'] as (keyof RulesChecks)[]).map(
                                    (category) => (
                                        <Card
                                            key={category}
                                            title={
                                                <>
                                                    <span className="text-md font-semibold">
                                                        {category === 'all' && 'All'}
                                                        {category === 'any' && 'Any'}
                                                        {category === 'none' && 'None'} Checks (
                                                        {checks[category].length})
                                                    </span>
                                                    <div className="text-xs text-gray-500">
                                                        {category === 'all' &&
                                                            'All checks in this category must pass.'}
                                                        {category === 'any' &&
                                                            'At least one check in this category must pass.'}
                                                        {category === 'none' &&
                                                            'No checks in this category must pass.'}
                                                    </div>
                                                </>
                                            }
                                            className="w-full min-w-[250px]"
                                        >
                                            <Droppable droppableId={category}>
                                                {(provided) => (
                                                    <ul
                                                        ref={provided.innerRef}
                                                        {...provided.droppableProps}
                                                        className="min-h-[40px] list-none p-0"
                                                    >
                                                        {checks[category].map((check, index) => (
                                                            <Draggable
                                                                key={`check-${check.id}`}
                                                                draggableId={`check-${check.id}`}
                                                                index={index}
                                                            >
                                                                {(provided, snapshot) => (
                                                                    <li
                                                                        ref={provided.innerRef}
                                                                        {...provided.draggableProps}
                                                                        {...provided.dragHandleProps}
                                                                        className={` bg-white border border-gray-200 rounded mb-2 px-3 py-2 shadow-sm cursor-grab transition-colors ${
                                                                            snapshot.isDragging
                                                                                ? 'bg-blue-100'
                                                                                : ''
                                                                        }`}
                                                                        style={
                                                                            provided.draggableProps
                                                                                .style
                                                                        }
                                                                    >
                                                                        <CheckComponent
                                                                            update={updateCheckFunction(
                                                                                category
                                                                            )}
                                                                            check={check}
                                                                        />
                                                                    </li>
                                                                )}
                                                            </Draggable>
                                                        ))}
                                                        {provided.placeholder}
                                                    </ul>
                                                )}
                                            </Droppable>
                                        </Card>
                                    )
                                )}
                            </div>
                        </DragDropContext>

                        <div className="text-gray-500 mb-4 mt-2 flex items-center gap-1">
                            <InfoCircleOutlined /> Double click to edit check
                        </div>
                    </div>
                    <Flex justify="space-left" gap={8} align="center">
                        <Button onClick={() => toggleCollapse(true)}>View Rule Details</Button>

                        <Button
                            type="primary"
                            onClick={() => setCheckModalOpen(true)}
                            icon={<PlusOutlined />}
                        >
                            Add Check
                        </Button>
                        <AddCheck
                            open={checkModalOpen}
                            onClose={async () => {
                                const checks = await fetchChecks(rule.id);
                                setChecks(checks);
                                setCheckModalOpen(false);
                            }}
                            rule={rule}
                        />
                    </Flex>
                </div>
            )}
        </Card>
    );
}
