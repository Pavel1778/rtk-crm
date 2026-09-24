import { useMemo } from 'react';
import { DatePicker, Space } from 'antd';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

export type DateRangeValue = { date_from?: string; date_to?: string };

type Props = {
  value: DateRangeValue;
  onChange: (value: DateRangeValue) => void;
  /** Подпись над полем; по умолчанию скрыта, если поле одно в форме. */
  label?: string;
  id?: string;
  disabled?: boolean;
  style?: React.CSSProperties;
};

/** Пресеты диапазонов в порядке частоты использования. */
function presets(): { label: string; value: [Dayjs, Dayjs] }[] {
  const today = dayjs().endOf('day');
  return [
    { label: 'Сегодня', value: [dayjs().startOf('day'), today] },
    { label: '7 дней', value: [dayjs().subtract(6, 'day').startOf('day'), today] },
    { label: '30 дней', value: [dayjs().subtract(29, 'day').startOf('day'), today] },
    { label: 'Этот месяц', value: [dayjs().startOf('month'), today] },
    {
      label: 'Прошлый месяц',
      value: [
        dayjs().subtract(1, 'month').startOf('month'),
        dayjs().subtract(1, 'month').endOf('month'),
      ],
    },
    {
      label: 'Квартал',
      value: [dayjs().subtract(2, 'month').startOf('month'), today],
    },
    { label: 'Год', value: [dayjs().startOf('year'), today] },
  ];
}

/**
 * Единый выбор диапазона дат: компактный вид «23.09.2026 — 29.09.2026»
 * вместо двух полей с подписями «С даты» / «По дату».
 *
 * Инвертированный диапазон (начало позже конца) автоматически меняется
 * местами, чтобы фильтр нельзя было отправить в заведомо пустом виде.
 */
export default function DateRangeFilter({
  value,
  onChange,
  label,
  id,
  disabled,
  style,
}: Props) {
  const pickerValue = useMemo<[Dayjs | null, Dayjs | null] | null>(() => {
    if (!value.date_from && !value.date_to) return null;
    return [
      value.date_from ? dayjs(value.date_from) : null,
      value.date_to ? dayjs(value.date_to) : null,
    ];
  }, [value.date_from, value.date_to]);

  const control = (
    <RangePicker
      id={id}
      disabled={disabled}
      value={pickerValue}
      presets={presets()}
      format="DD.MM.YYYY"
      placeholder={['дд.мм.гггг', 'дд.мм.гггг']}
      allowEmpty={[true, true]}
      style={{ width: '100%', ...style }}
      onChange={(range) => {
        let start = range?.[0] ?? null;
        let end = range?.[1] ?? null;
        // Пользователь ввёл диапазон в обратном порядке — меняем местами.
        if (start && end && start.isAfter(end, 'day')) {
          [start, end] = [end, start];
        }
        onChange({
          date_from: start ? start.format('YYYY-MM-DD') : undefined,
          date_to: end ? end.format('YYYY-MM-DD') : undefined,
        });
      }}
    />
  );

  if (!label) {
    return <div className="date-range-filter">{control}</div>;
  }

  return (
    <Space direction="vertical" size={4} className="date-range-filter">
      <span className="date-range-filter__label">{label}</span>
      {control}
    </Space>
  );
}
