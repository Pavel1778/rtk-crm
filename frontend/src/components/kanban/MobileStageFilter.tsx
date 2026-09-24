import type { BoardColumn } from '../../types';

interface Props {
  columns: BoardColumn[];
  value: number | undefined;
  onChange: (value: number | undefined) => void;
}

/**
 * Переключатель этапов для узкого экрана: на телефоне показываем одну
 * колонку вместо длинной вертикальной простыни из всех этапов.
 * Чипы прокручиваются по горизонтали и показывают счётчик карточек.
 */
export default function MobileStageFilter({ columns, value, onChange }: Props) {
  return (
    <div className="stage-chips" role="tablist" aria-label="Этапы воронки">
      <button
        type="button"
        role="tab"
        aria-selected={value === undefined}
        className={`stage-chip${value === undefined ? ' stage-chip--active' : ''}`}
        onClick={() => onChange(undefined)}
      >
        Все этапы
      </button>
      {columns.map((column) => {
        const selected = value === column.stage.id;
        return (
          <button
            key={column.stage.id}
            type="button"
            role="tab"
            aria-selected={selected}
            className={`stage-chip${selected ? ' stage-chip--active' : ''}`}
            onClick={() => onChange(column.stage.id)}
          >
            <span
              className="stage-chip__dot"
              style={{ background: column.stage.color ?? 'var(--atmr-accent-default)' }}
            />
            {column.stage.name}
            <span className="stage-chip__count">{column.interactions.length}</span>
          </button>
        );
      })}
    </div>
  );
}
