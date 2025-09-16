'use client';
import PageLoading from '@/components/PageLoading';
import { Check } from '@/lib/types/axe';
import { useRules } from '@/providers/Rules';
import { Editor } from '@monaco-editor/react';
import { Button, Flex, Form, Input, Modal, Tooltip } from 'antd';
import { useState } from 'react';

type Props = {
    check: Check;
    update: (updatedCheck: Check, deleted?: boolean) => Promise<void>;
};

function CheckComponent({ check, update }: Props) {
    const { validateCheckRule, updateCheck, deleteCheck } = useRules();
    const [showEditModal, setShowEditModal] = useState(false);
    const [showDeleteModal, setShowDeleteModal] = useState(false);
    const [showOptions, setShowOptions] = useState(check.evaluate.includes('(node, options,'));
    const [form] = Form.useForm<Check>();

    const onFinish = async (values: Check) => {
        // Handle form submission logic here
        await form.validateFields();
        // You can call an API or update the state with the new values
        const new_check = await updateCheck(check.id, values);
        if (new_check) {
            await update(new_check);
        }

        setShowEditModal(false);
    };

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

    const evalCommentFunction = `/**
 * Evaluation function for the check. A successful evaluation returns true.
 * 
 * @param {HTMLElement} node
 * @param {{}} options
 * @param {HTMLElement} virtualNode
 * @returns {boolean}
 */
`;

    return (
        <>
            {' '}
            <Tooltip title="Edit check" placement="bottom">
                <Flex
                    justify="space-between"
                    align="center"
                    className="p-2"
                    onDoubleClick={() => setShowEditModal(true)}
                >
                    <h3 className="text-lg font-medium">{check.name}</h3>
                    <p className="text-gray-600">{check.impact}</p>
                </Flex>
            </Tooltip>
            <Form form={form} layout="vertical" onFinish={onFinish}>
                <Modal
                    title={`Edit Check: ${check.name}`}
                    open={showEditModal}
                    onCancel={() => setShowEditModal(false)}
                    footer={
                        <div className="flex justify-end gap-2">
                            <Button
                                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                                onClick={() => setShowDeleteModal(true)}
                            >
                                Delete
                            </Button>
                            <Button
                                className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
                                onClick={() => setShowEditModal(false)}
                            >
                                Cancel
                            </Button>
                            <Button
                                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                                htmlType="submit"
                                key={'submit'}
                                type="primary"
                                onClick={() => form.submit()}
                            >
                                Save
                            </Button>
                        </div>
                    }
                    width={800}
                >
                    <Form.Item label="Evaluation Function" required>
                        <Form.Item
                            noStyle
                            name="evaluate"
                            validateDebounce={300}
                            validateTrigger="onChange"
                            rules={[{ required: true }, { validator: CheckEvaluationFunction }]}
                            initialValue={evalCommentFunction + check.evaluate}
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
                        <div className="text-sm text-gray-500 mt-1">
                            Example:
                            <code>{`(node, options, virtualNode) => node.getAttribute('role') === 'button'`}</code>
                        </div>
                    </Form.Item>
                    {showOptions && (
                        <Form.Item label="Options (JSON)">
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
                                initialValue={JSON.stringify(check.options, null, 2)}
                            >
                                <Input.TextArea rows={4} placeholder='e.g. { "key": "value" }' />
                            </Form.Item>
                            <div className="text-sm text-gray-500">
                                Options must be a valid JSON object. This will be passed as the
                                second argument to the evaluation function.
                            </div>
                        </Form.Item>
                    )}

                    <Form.Item
                        label="Pass Text"
                        name="pass_text"
                        initialValue={check.pass_text}
                        rules={[{ required: true, message: 'Please input the pass text!' }]}
                    >
                        <Input />
                    </Form.Item>
                    <Form.Item
                        label="Fail Text"
                        name="fail_text"
                        initialValue={check.fail_text}
                        rules={[{ required: true, message: 'Please input the fail text!' }]}
                    >
                        <Input />
                    </Form.Item>
                    <Form.Item
                        label="Incomplete Text"
                        name="incomplete_text"
                        rules={[{ required: false }]}
                        initialValue={check.incomplete_text}
                    >
                        <Input />
                    </Form.Item>
                </Modal>
            </Form>
            <Modal
                open={showDeleteModal}
                onCancel={() => setShowDeleteModal(false)}
                onOk={async () => {
                    try {
                        await deleteCheck(check.id);
                        await update(check, true); // Trigger parent update with dummy check
                    } catch (error) {
                        console.error('Failed to delete check:', error);
                        if (error instanceof Error) {
                            if (error.message.includes('Not Found')) {
                                update(check, true); // Trigger parent update with dummy check
                            }
                        }
                    }
                    setShowDeleteModal(false);
                    setShowEditModal(false);
                }}
                title="Delete Check"
                okText="Delete"
                okButtonProps={{ danger: true }}
            >
                <p>Are you sure you want to delete this check?</p>
            </Modal>
        </>
    );
}

export default CheckComponent;
