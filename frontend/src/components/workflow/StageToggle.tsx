import { Switch, App } from 'antd';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../api/client';

interface Props {
  stageId: number;
  isActive: boolean;
  disabled?: boolean;
}

export default function StageToggle({ stageId, isActive, disabled }: Props) {
  const { message } = App.useApp();
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: async (next: boolean) => {
      const res = await api.patch(`/api/stages/${stageId}`, { is_active: next });
      return res.data;
    },
    onMutate: async (next) => {
      await qc.cancelQueries({ queryKey: ['stages'] });
      const prev = qc.getQueryData<any[]>(['stages']);
      qc.setQueryData<any[]>(['stages'], old =>
        (old ?? []).map(s => s.id === stageId ? { ...s, is_active: next } : s)
      );
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) qc.setQueryData(['stages'], ctx.prev);
      message.error('Не удалось изменить этап');
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['stages'] }),
  });

  return (
    <Switch
      checked={isActive}
      loading={mutation.isPending}
      disabled={disabled}
      onChange={(next) => mutation.mutate(next)}
      aria-label="Активен"
    />
  );
}
