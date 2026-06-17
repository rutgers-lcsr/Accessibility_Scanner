import { Input, Tooltip } from 'antd';
import type { InputRef } from 'antd';
import { useEffect, useRef, useState } from 'react';

type Props<T> = Omit<React.ComponentProps<typeof Input>, 'onChange'> & {
    label?: string;
    value: T;
    validate?: (value: T) => string | null;
    onChange: (value: T) => Promise<void>;
};

function EditableInput<T>({ label, value, onChange, validate, ...rest }: Props<T>) {
    const [isEditing, setIsEditing] = useState(false);
    const [localValue, setLocalValue] = useState<T>(value);
    const [error, setError] = useState<string | null>(null);
    const inputRef = useRef<InputRef>(null);
    // Focus the input when entering edit mode
    useEffect(() => {
        if (isEditing) {
            inputRef.current?.focus();
        }
    }, [isEditing]);
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
    if (isEditing) {
        return (
            <div>
                {label && <strong>{label}: </strong>}
                <Input
                    {...rest}
                    value={localValue as unknown as string}
                    onPressEnter={async (e) => {
                        e.preventDefault();
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
                        await onChange((e.target as HTMLInputElement).value as unknown as T);
                        setIsEditing(false);
                    }}
                    onChange={(e) => setLocalValue(e.target.value as unknown as T)}
                    onBlur={() => setIsEditing(false)}
                    ref={inputRef}
                    aria-label={label ? `${label} input` : 'Editable input'}
                    className={`w-full ${error ? 'border-red-500' : ''}`}
                    data-testid="editable-input"
                />
                {error && <div className="text-red-500">{error}</div>}
            </div>
        );
    }

    return (
        <Tooltip title={'Click to edit' + (label ? ` ${label}` : '')} placement="top">
            <button
                type="button"
                onClick={() => setIsEditing(true)}
                className="block w-full text-left"
                style={{ cursor: 'pointer', minHeight: '32px' }}
                aria-label={label ? `${label} value` : 'Editable input value'}
            >
                {label && <strong>{label}: </strong>}
                <span className="underline">{value}</span>
            </button>
        </Tooltip>
    );
}

export default EditableInput;
