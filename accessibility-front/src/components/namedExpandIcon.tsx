'use client';
import type { TableProps } from 'antd';
import type { ComponentProps, ComponentType } from 'react';

// antd's own types, so no import from its internal table package.
type ExpandIcon<T> = NonNullable<NonNullable<TableProps<T>['components']>['ExpandIcon']>;
type ExpandIconProps<T> = ComponentProps<ExpandIcon<T>>;

// An antd Table expand button named after its row ("History of https://…"): antd's own is
// called "Expand row" on every row, which tells a screen-reader user nothing. Pass the
// result as `components={{ ExpandIcon }}` (antd 6; expandable.expandIcon is deprecated).
export function namedExpandIcon<T>(name: (record: T) => string): ComponentType<ExpandIconProps<T>> {
    function NamedExpandIcon(props: ExpandIconProps<T>) {
        const base = `${props.prefixCls}-row-expand-icon`;
        if (props.type !== 'row') return null;
        if (!props.expandable) return <span className={`${base} ${base}-spaced`} />;
        return (
            <button
                type="button"
                className={`${base} ${base}-${props.expanded ? 'expanded' : 'collapsed'}`}
                aria-expanded={props.expanded}
                aria-label={name(props.record)}
                onClick={props.onClick}
            />
        );
    }
    return NamedExpandIcon;
}
