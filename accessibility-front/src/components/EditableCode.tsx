import { Editor } from '@monaco-editor/react';
import { Button, Form } from 'antd';
import { useState } from 'react';
import PageLoading from './PageLoading';

type Props = {
    label?: string;
    value: string;
    validate?: (value: string) => string | null;
    onChange: (value: string) => Promise<void>;
};

function EditableCode({ label, value, onChange, validate }: Props) {
    const [isEditing, setIsEditing] = useState(false);
    const [localValue, setLocalValue] = useState(value);
    const [error, setError] = useState<string | null>(null);

    // Update local value if the prop value changes
    if (value !== localValue && !isEditing) {
        setLocalValue(value);
    }

    // Validate on local value change
    if (validate) {
        const validationError = validate(localValue);
        if (validationError !== error) {
            setError(validationError);
        }
    }

    const submitEdit = async () => {
        if (validate) {
            const validationError = validate(localValue);
            if (validationError) {
                setError(validationError);
                return;
            }
        }
        if (localValue === value) {
            setIsEditing(false);
            return;
        }
        await onChange(localValue);
        setIsEditing(false);
    };

    if (isEditing) {
        return (
            <Form layout="vertical" className="relative" onBlur={submitEdit} onFinish={submitEdit}>
                {label && <strong>{label}: </strong>}
                <Form.Item
                    noStyle
                    name="matches"
                    validateDebounce={300}
                    validateTrigger="onChange"
                    rules={[
                        { required: false },
                        {
                            validator: () => {
                                if (validate) {
                                    const validationError = validate(localValue);
                                    if (validationError) {
                                        return Promise.reject(new Error(validationError));
                                    }
                                }
                                return Promise.resolve();
                            },
                        },
                    ]}
                >
                    <Editor
                        defaultLanguage="javascript"
                        theme="vs-light"
                        height="100px"
                        defaultValue={localValue}
                        onChange={(value) => setLocalValue(value || '')}
                        loading={<PageLoading minimal />}
                    />
                </Form.Item>
                <Form.Item className="text-right mb-0">
                    <Button type="primary" htmlType="submit">
                        Save
                    </Button>
                </Form.Item>
                {error && <div className="text-red-500">{error}</div>}
            </Form>
        );
    }

    return (
        <div onClick={() => setIsEditing(true)} style={{ cursor: 'pointer' }}>
            {label && <strong>{label}: </strong>}
            <span>{value}</span>
        </div>
    );
}

export default EditableCode;
