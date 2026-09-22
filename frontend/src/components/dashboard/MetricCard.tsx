import { Typography } from 'antd';
import type { ReactNode } from 'react';

const { Text } = Typography;

interface Props {
  label: string;
  value: number | string;
  icon?: ReactNode;
  color?: string;
  hint?: string;
}

export default function MetricCard({
  label,
  value,
  icon,
  color,
  hint,
}: Props) {
  return (
    <div
      className="stat-card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        background: '#fff',
        border: '1px solid var(--atmr-border-soft)',
        borderRadius: 12,
        padding: 'clamp(12px, 2vw, 20px)',
        minHeight: 100,
        height: '100%',
        boxSizing: 'border-box',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: 12,
        }}
      >
        <Text
          style={{
            fontSize: 12,
            fontWeight: 500,
            color: 'var(--atmr-fg-muted)',
            textTransform: 'uppercase',
            letterSpacing: 0.3,
            lineHeight: 1.3,
          }}
        >
          {label}
        </Text>
        {icon && (
          <span
            style={{
              fontSize: 20,
              color: 'var(--atmr-accent-default)',
              opacity: 0.7,
              flexShrink: 0,
            }}
          >
            {icon}
          </span>
        )}
      </div>

      <div style={{ marginTop: 12 }}>
        <div
          style={{
            fontSize: 28,
            fontWeight: 700,
            lineHeight: 1.1,
            color: color || 'var(--atmr-fg-default)',
          }}
        >
          {value}
        </div>
        {hint && (
          <Text
            style={{
              fontSize: 11,
            color: 'var(--atmr-fg-muted)',
              marginTop: 4,
              display: 'block',
            }}
          >
            {hint}
          </Text>
        )}
      </div>
    </div>
  );
}
