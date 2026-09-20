import { Card, Typography } from 'antd';
import type { ReactNode } from 'react';

const { Text } = Typography;

interface Props {
  label: string;
  value: number | string;
  icon?: ReactNode;
  color?: string;
  hint?: string;
}

export default function MetricCard({ label, value, icon, color, hint }: Props) {
  return (
    <Card
      styles={{ body: { padding: '16px 20px' } }}
      style={{
        height: '100%',
        borderRadius: 12,
        border: '1px solid var(--atmr-border-soft, #EEEEF2)',
        boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <Text
            style={{
              fontSize: 12,
              color: 'var(--atmr-fg-muted, #6B6B72)',
              display: 'block',
              marginBottom: 8,
              textTransform: 'uppercase',
              letterSpacing: 0.3,
              fontWeight: 500,
            }}
          >
            {label}
          </Text>
          <div
            style={{
              fontSize: 28,
              fontWeight: 700,
              color: color || 'var(--atmr-fg-default, #1C1D22)',
              lineHeight: 1.1,
              marginBottom: hint ? 4 : 0,
            }}
          >
            {value}
          </div>
          {hint && (
            <Text style={{ fontSize: 11, color: 'var(--atmr-fg-muted, #6B6B72)' }}>
              {hint}
            </Text>
          )}
        </div>
        {icon && (
          <div
            style={{
              fontSize: 24,
              color: 'var(--atmr-accent-default, #6E41F2)',
              opacity: 0.6,
              marginLeft: 12,
            }}
          >
            {icon}
          </div>
        )}
      </div>
    </Card>
  );
}
