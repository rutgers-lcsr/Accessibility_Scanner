import { AxeResult } from '@/lib/types/axe'
import React from 'react'
import { Card, Tag } from 'antd'

type Props = {
  accessibilityResult: AxeResult
}

function AuditAccessibilityItem({ accessibilityResult }: Props) {
  return (
    <Card
      style={{ marginBottom: '16px' }}
      title={
        <span className="font-semibold text-lg">
          {accessibilityResult.id}
        </span>
      }
      extra={
        <Tag color={accessibilityResult.impact === 'critical' ? 'red' : 'blue'}>
          {accessibilityResult.impact}
        </Tag>
      }
    >
      <div className="mb-2 text-gray-700">{accessibilityResult.description}</div>
      <div className="text-sm text-gray-500">
        <strong>Help:</strong> {accessibilityResult.help}
      </div>

      {accessibilityResult.nodes && (
        <div className="mt-2">
          <strong>Nodes:</strong>
          <ul className="list-disc list-inside">
            {accessibilityResult.nodes.map((node, idx) => (
              <li key={idx} className="text-xs text-gray-600">
                {node.target.join(', ')}
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-2 justify-end flex flex-wrap gap-2">
        {accessibilityResult.tags && accessibilityResult.tags.map((tag, index) => (
          <Tag key={index} color="default">
            {tag}
          </Tag>
        ))}
      </div>
      <div className='mt-2 justify-end-safe flex'>
        <a href={accessibilityResult.helpUrl} target="_blank" rel="noopener noreferrer">
          Learn more
        </a>
      </div>

    </Card>
  )
}

export default AuditAccessibilityItem