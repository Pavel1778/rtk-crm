import { Button } from 'antd';
import { InboxOutlined } from '@ant-design/icons';

interface Props {
  title: string;
  description?: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}

export default function EmptyState({ 
  title, description, actionLabel, onAction, icon 
}: Props) {
  return (
    <div style={{
      textAlign: 'center', padding: '60px 20px',
      color: 'var(--atmr-fg-muted)',
    }}>
      <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.4 }}>
        {icon || <InboxOutlined />}
      </div>
      <h3 style={{ fontSize: 16, marginBottom: 8, color: 'var(--atmr-fg-default)' }}>
        {title}
      </h3>
      {description && (
        <p style={{ fontSize: 13, marginBottom: 16 }}>{description}</p>
      )}
      {actionLabel && onAction && (
        <Button type="primary" onClick={onAction}>{actionLabel}</Button>
      )}
    </div>
  );
}
