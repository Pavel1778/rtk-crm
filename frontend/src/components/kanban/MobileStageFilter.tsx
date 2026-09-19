import { Select } from 'antd';

import type { BoardColumn } from '../../types';

interface Props {
  columns: BoardColumn[];
  value: number | undefined;
  onChange: (value: number | undefined) => void;
}

/**
 * Фильтр этапов для мобильной версии: на узком экране показывается
 * одна колонка вместо горизонтальной прокрутки всей доски.
 */
export default function MobileStageFilter({ columns, value, onChange }: Props) {
  return (
    <Select
      placeholder="Этап"
      allowClear
      style={{ width: 160 }}
      value={value}
      onChange={onChange}
      options={columns.map((column) => ({
        value: column.stage.id,
        label: `${column.stage.name} (${column.interactions.length})`,
      }))}
    />
  );
}
