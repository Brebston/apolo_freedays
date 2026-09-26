import { monthName, parseISODate, weekdays } from '../i18n'

/** Рядок квоти: кожна точка — один день ліміту. Сіра — вже використано, акцентна — обрано зараз. */
export function Quota({ limit, used, selected, label }) {
  const showPips = limit <= 15
  const free = Math.max(limit - used - selected, 0)
  return (
    <div className="quota" aria-label={label}>
      {showPips ? (
        <div className="quota-pips" aria-hidden="true">
          {Array.from({ length: used }, (_, i) => <span key={`u${i}`} className="pip pip-used" />)}
          {Array.from({ length: selected }, (_, i) => <span key={`s${i}`} className="pip pip-selected" />)}
          {Array.from({ length: free }, (_, i) => <span key={`f${i}`} className="pip" />)}
        </div>
      ) : (
        <div className="quota-bar" aria-hidden="true">
          <span className="quota-bar-used" style={{ width: `${(used / limit) * 100}%` }} />
          <span className="quota-bar-selected" style={{ width: `${(selected / limit) * 100}%` }} />
        </div>
      )}
      <span className="quota-label">{label}</span>
    </div>
  )
}

export function Calendar({ lang, year, month, days, selected, today, canPrev, onPrev, onNext, onDayClick }) {
  const firstWeekday = (new Date(year, month - 1, 1).getDay() + 6) % 7 // понеділок = 0
  const selectedSet = new Set(selected)

  return (
    <div className="calendar">
      <div className="calendar-head">
        <button type="button" className="calendar-nav" onClick={onPrev} disabled={!canPrev} aria-label="‹">‹</button>
        <span className="calendar-month">{monthName(lang, month)} {year}</span>
        <button type="button" className="calendar-nav" onClick={onNext} aria-label="›">›</button>
      </div>

      <div className="calendar-grid" role="grid">
        {weekdays(lang).map((name, index) => (
          <span key={name} className={`calendar-weekday${index >= 5 ? ' is-weekend' : ''}`}>{name}</span>
        ))}
        {Array.from({ length: firstWeekday }, (_, i) => <span key={`pad${i}`} />)}

        {days
          ? days.map(({ date, state }) => {
            const isSelected = selectedSet.has(date)
            const classes = ['day', `day-${state}`]
            if (isSelected) classes.push('is-selected')
            if (date === today) classes.push('is-today')
            return (
              <button
                key={date}
                type="button"
                role="gridcell"
                className={classes.join(' ')}
                disabled={state === 'past'}
                aria-pressed={isSelected}
                onClick={() => onDayClick(date, state)}
              >
                {parseISODate(date).getDate()}
              </button>
            )
          })
          : Array.from({ length: new Date(year, month, 0).getDate() }, (_, i) => (
            <span key={`sk${i}`} className="day day-skeleton" />
          ))}
      </div>
    </div>
  )
}

export function Legend({ t, type }) {
  return (
    <div className="legend">
      <span><i className="legend-swatch swatch-selected" />{t('legendSelected')}</span>
      <span><i className="legend-swatch swatch-mine" />{t('legendMine')}</span>
      {type === 'dayoff' && <span><i className="legend-swatch swatch-full" />{t('legendFull')}</span>}
    </div>
  )
}
