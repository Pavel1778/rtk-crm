import { Switch, Tooltip } from 'antd';

import { useToggleStage } from '../../hooks/useStages';

interface Props {
  stageId: number;
  isActive: boolean;
  disabled?: boolean;
}

export default function StageToggle({ stageId, isActive, disabled }: Props) {
  const toggle = useToggleStage('all');

  return (
    <Tooltip title={isActive ? 'Выключить этап' : 'Включить этап'}>
      <Switch
        checked={isActive}
        loading={toggle.isPending}
        disabled={disabled}
        onChange={(next) => toggle.mutate({ id: stageId, isActive: next })}
        aria-label={`Этап ${stageId}: ${isActive ? 'активен' : 'неактивен'}`}
      />
    </Tooltip>
  );
}
