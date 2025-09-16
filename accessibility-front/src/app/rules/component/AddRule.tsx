'use client';
import PageLoading from '@/components/PageLoading';
import { RuleTemplate } from '@/lib/types/axe';
import { useRules } from '@/providers/Rules';
import Editor from '@monaco-editor/react';
import { Button, Flex, Form, Input, Modal, Select, Switch } from 'antd';
import { useState } from 'react';
const { Option } = Select;
type AddRuleProps = {
    tags?: string[];
    open?: boolean;
    onClose?: () => void;
};

export default function AddRule({ open, onClose }: AddRuleProps) {
    const [form] = Form.useForm<RuleTemplate>();
    const [loading, setLoading] = useState(false);
    const { validateMatchRule, addRule, tags } = useRules();

    const CheckMatchFunction = async (_: unknown, value: string) => {
        // Implement your logic to check the match function here
        // For example, you might want to validate the function syntax or test it against some sample data
        if (!value) {
            return Promise.resolve(); // If no match function is provided, consider it valid
        }

        const isValid = await validateMatchRule(value);
        if (isValid) {
            return Promise.resolve();
        } else {
            return Promise.reject(new Error('Invalid match function'));
        }
    };

    const onFinish = async (values: RuleTemplate) => {
        setLoading(true);
        try {
            const success = await addRule(values);
            if (success) {
                await onClose?.();
                form.resetFields();
            }
        } finally {
            setLoading(false);
        }
    };

    const matchFunctionInitialValue = `/**
 * This function should return true if the node matches the rule, and false otherwise.
 * @param {HTMLElement} node - The DOM node to check.
 * @returns {boolean} - Whether the node matches the rule.
 */
(node) => {
    // Example: Check if the node is an image without alt text
    return node.tagName === 'IMG' && !node.hasAttribute('alt');
}`;

    return (
        <Modal
            open={open}
            onCancel={() => {
                form.resetFields();
                if (onClose) onClose();
            }}
            footer={null}
            title="Add Rule"
            destroyOnHidden
            width={800}
            loading={loading}
            centered
        >
            <Form form={form} layout="vertical" onFinish={onFinish}>
                <Form.Item
                    label="Rule Name"
                    name="name"
                    rules={[{ required: true, message: 'Please input the rule name!' }]}
                    extra="A unique name for the rule."
                >
                    <Input />
                </Form.Item>

                <Form.Item
                    label="Description"
                    name="description"
                    rules={[{ required: true, message: 'Please input the description!' }]}
                    extra="A description of what the rule checks for. This will be shown in the report."
                >
                    <Input />
                </Form.Item>
                <Flex gap={16} className="mb-4" wrap="unset">
                    <Form.Item
                        label="Impact"
                        name="impact"
                        initialValue={'minor'}
                        rules={[{ required: true, message: 'Please select the impact!' }]}
                        extra="The severity of the issue if this rule is violated."
                    >
                        <Select style={{ width: 200 }} placeholder="Select impact">
                            <Option value="minor">Minor</Option>
                            <Option value="moderate">Moderate</Option>
                            <Option value="serious">Serious</Option>
                            <Option value="critical">Critical</Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        label="Tags"
                        name="tags"
                        rules={[{ required: true, message: 'Please input the tags!' }]}
                        extra="Tags to categorize the rule. You can select existing tags or create new ones."
                    >
                        <Select mode="tags" placeholder="Select or create tags">
                            {(tags &&
                                tags.map((tag) => (
                                    <Option key={tag} value={tag}>
                                        {tag}
                                    </Option>
                                ))) ||
                                null}
                        </Select>
                    </Form.Item>
                    <Form.Item
                        label="Exclude Hidden Elements"
                        name="exclude_hidden"
                        valuePropName="checked"
                        extra="Whether to exclude hidden elements (e.g., display: none) from being checked by this rule."
                    >
                        <Switch defaultChecked />
                    </Form.Item>
                </Flex>

                <Form.Item
                    label="Match Function"
                    extra="A JavaScript function that determines if a DOM node matches the rule. It should return true if the node matches, and false otherwise. If no function is provided, the rule will apply to all elements that pass the selector."
                >
                    <Form.Item
                        noStyle
                        name="matches"
                        validateDebounce={300}
                        validateTrigger="onChange"
                        initialValue={matchFunctionInitialValue}
                        rules={[{ required: false }, { validator: CheckMatchFunction }]}
                    >
                        <Editor
                            defaultLanguage="javascript"
                            theme="vs-light"
                            height="200px"
                            loading={<PageLoading minimal />}
                        />
                    </Form.Item>
                </Form.Item>

                <Form.Item
                    label="Selector"
                    name="selector"
                    rules={[
                        { required: false },
                        {
                            validator: (_, value) => {
                                try {
                                    document.querySelector(value);
                                    return Promise.resolve();
                                } catch {
                                    return Promise.reject(new Error('Invalid CSS selector'));
                                }
                            },
                        },
                    ]}
                    initialValue={'*'}
                    extra="A CSS selector to narrow down the elements the rule applies to. Defaults to '*' (all elements)."
                >
                    <Input />
                </Form.Item>
                <Form.Item
                    label="Help Text"
                    name="help"
                    rules={[{ required: true, message: 'Please input the help text!' }]}
                    extra="Text that will be shown to users to help them fix the issue."
                >
                    <Input.TextArea rows={4} />
                </Form.Item>
                <Form.Item
                    label="Help URL"
                    name="help_url"
                    rules={[
                        { required: true, message: 'Please input the help URL!' },
                        { type: 'url', message: 'Please enter a valid URL!' },
                    ]}
                    extra="A URL to a page with more information about the issue and how to fix it."
                >
                    <Input />
                </Form.Item>

                <Form.Item>
                    <div className="flex justify-end mb-4 text-sm text-gray-500">
                        <Button size="large" type="primary" htmlType="submit">
                            Add Rule
                        </Button>
                    </div>
                </Form.Item>
            </Form>
        </Modal>
    );
}
