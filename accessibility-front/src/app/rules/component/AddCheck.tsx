'use client';

import PageLoading from '@/components/PageLoading';
import { CheckTemplate, Rule } from '@/lib/types/axe';
import { useRules } from '@/providers/Rules';
import { PlusOutlined } from '@ant-design/icons';
import { Editor } from '@monaco-editor/react';
import { Button, Flex, Form, Input, Modal, Select } from 'antd';
import { useState } from 'react';

const { Option } = Select;

type Props = {
    rule: Rule;
    open: boolean;
    onClose: () => Promise<void>;
};

export default function AddCheck({ open, onClose, rule }: Props) {
    const { validateCheckRule, addCheck, updateRule, checkNames } = useRules();
    const [loading, setLoading] = useState(false);
    const [showOptions, setShowOptions] = useState(true);
    const [form] = Form.useForm<CheckTemplate>();

    const CheckEvaluationFunction = async (_: unknown, value: string) => {
        if (!value) {
            return Promise.resolve(); // If no evaluation function is provided, consider it valid
        }
        if (value.includes('(node, options,')) {
            setShowOptions(true);
        } else {
            setShowOptions(false);
            form.setFieldValue('options', '');
        }

        const isValid = await validateCheckRule(value);
        if (isValid) {
            return Promise.resolve();
        } else {
            return Promise.reject(new Error('Invalid Evaluation function'));
        }
    };
    const onFinish = async (values: CheckTemplate) => {
        setLoading(true);
        try {
            const check = await addCheck(values);
            if (check) {
                const ruleCheck = rule[values.type as keyof Rule] as number[];
                ruleCheck.push(check.id);
                await updateRule(rule.id, { [values.type]: ruleCheck });
                if (onClose) await onClose();
                form.resetFields();
            }
        } catch (error) {
            console.error('Failed to add check:', error);
        } finally {
            setLoading(false);
        }
    };
    const onCancel = () => {
        if (onClose) onClose();
    };

    const defaultEval = `/**
 * Evaluation function for the check. A successful evaluation returns true.
 * 
 * @param {HTMLElement} node
 * @param {{}} options
 * @param {HTMLElement} virtualNode
 * @returns {boolean}
 */
(node, options, virtualNode) => {
    // Example: Check if the node has a role of 'button'
    return node.getAttribute('role') === 'button';
}`;

    return (
        <Form form={form} layout="vertical" onFinish={onFinish}>
            <Modal
                open={open}
                onCancel={onCancel}
                title={`Add Check to ${rule.name}`}
                width={800}
                footer={
                    <Form.Item>
                        <Button
                            itemType="submit"
                            key={'submit'}
                            type="primary"
                            loading={loading}
                            icon={<PlusOutlined />}
                            htmlType="submit"
                            onClick={() => form.submit()}
                        >
                            Add Check
                        </Button>
                    </Form.Item>
                }
                destroyOnHidden
                loading={loading}
                centered
            >
                <Flex gap="large">
                    <Form.Item
                        style={{ flex: 4 }}
                        label="Check Name"
                        name="name"
                        extra="A unique name for the check."
                        rules={[
                            { required: true, message: 'Please input the check name!' },
                            {
                                validator: async (_, value) => {
                                    if (!value) return Promise.resolve();
                                    if (
                                        checkNames &&
                                        checkNames.find((check) => check.name === value)
                                    ) {
                                        return Promise.reject(
                                            new Error('Check name must be unique')
                                        );
                                    }
                                    return Promise.resolve();
                                },
                            },
                        ]}
                    >
                        <Input />
                    </Form.Item>
                    <Form.Item
                        label="Type"
                        name="type"
                        required
                        initialValue="all"
                        style={{ flex: 3 }}
                        rules={[{ required: true, message: 'Please select the type!' }]}
                        tooltip={{
                            title: (
                                <>
                                    <strong>Check type:</strong> Determines how the check is
                                    evaluated.
                                    <br />
                                    <ul style={{ paddingLeft: 16, margin: 0 }}>
                                        <li>
                                            <b>Must Pass</b>: All checks must pass.
                                        </li>
                                        <li>
                                            <b>Can Pass</b>: At least one check must pass.
                                        </li>
                                        <li>
                                            <b>Should not pass</b>: No checks should pass.
                                        </li>
                                    </ul>
                                </>
                            ),
                            placement: 'bottom',
                        }}
                    >
                        <Select>
                            <Option value="all">Must Pass (all)</Option>
                            <Option value="any">Can Pass (any)</Option>
                            <Option value="none">Should not pass (none)</Option>
                        </Select>
                    </Form.Item>
                </Flex>

                <Form.Item
                    label="Evaluation Function"
                    required
                    extra="A JavaScript function that evaluates whether a DOM node passes the check. It should return true if the node passes, and false otherwise."
                >
                    <Form.Item
                        noStyle
                        name="evaluate"
                        validateDebounce={300}
                        validateTrigger="onChange"
                        rules={[{ required: true }, { validator: CheckEvaluationFunction }]}
                        initialValue={defaultEval}
                    >
                        <Editor
                            defaultLanguage="javascript"
                            // defaultValue={defaultEval}
                            theme="vs-light"
                            height="200px"
                            className="border border-gray-300 rounded"
                            loading={<PageLoading minimal />}
                        />
                    </Form.Item>
                </Form.Item>
                {showOptions && (
                    <Form.Item
                        label="Options (JSON)"
                        extra="Optional configuration options for the evaluation function."
                        name="options"
                    >
                        <Form.Item
                            noStyle
                            name="options"
                            rules={[
                                {
                                    validator: (_, value) => {
                                        if (!value) return Promise.resolve();
                                        try {
                                            JSON.parse(value);
                                            return Promise.resolve();
                                        } catch {
                                            return Promise.reject(new Error('Invalid JSON'));
                                        }
                                    },
                                },
                            ]}
                        >
                            <Input.TextArea rows={4} placeholder='e.g. { "key": "value" }' />
                        </Form.Item>
                    </Form.Item>
                )}

                <Form.Item
                    label="Pass Text"
                    name="pass_text"
                    extra="Text to display when the check passes."
                    rules={[{ required: true, message: 'Please input the pass text!' }]}
                >
                    <Input />
                </Form.Item>
                <Form.Item
                    label="Fail Text"
                    name="fail_text"
                    extra="Text to display when the check fails."
                    rules={[{ required: true, message: 'Please input the fail text!' }]}
                >
                    <Input />
                </Form.Item>
                <Form.Item
                    label="Incomplete Text"
                    name="incomplete_text"
                    extra="Text to display when the check is incomplete."
                    rules={[{ required: false }]}
                >
                    <Input />
                </Form.Item>
            </Modal>
        </Form>
    );
}
