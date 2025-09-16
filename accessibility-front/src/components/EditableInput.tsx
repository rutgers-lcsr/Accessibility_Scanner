import { Input } from 'antd';
import { useState } from 'react';

type Props = Omit<React.ComponentProps<typeof Input>, 'onChange'> & {
    label?: string;
    value: string | number;
    validate?: (value: string | number) => string | null;
    onChange: (value: string | number) => Promise<void>;
};

function EditableInput({ label, value, onChange, validate, ...rest }: Props) {
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
    if (isEditing) {
        return (
            <div>
                {label && <strong>{label}: </strong>}
                <Input
                    {...rest}
                    value={localValue}
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
                        await onChange((e.target as HTMLInputElement).value);
                        setIsEditing(false);
                    }}
                    onChange={(e) => setLocalValue(e.target.value)}
                    onBlur={() => setIsEditing(false)}
                    autoFocus
                    aria-label={label ? `${label} input` : 'Editable input'}
                    className={`w-full ${error ? 'border-red-500' : ''}`}
                    data-testid="editable-input"
                />
                {error && <div className="text-red-500">{error}</div>}
            </div>
        );
    }

    return (
        <div
            onClick={() => setIsEditing(true)}
            style={{ cursor: 'pointer' }}
            aria-label={label ? `${label} value` : 'Editable input value'}
        >
            {label && <strong>{label}: </strong>}
            <span>{value}</span>
        </div>
    );
}

export default EditableInput;
