import { useApp, useScreen } from '../context'
import { useBackButton } from '../telegram'

export function Screen({ title, subtitle, onBack, children }) {
  const { t, nav } = useApp()
  const screen = useScreen()
  const back = onBack ?? (screen?.canGoBack ? nav.pop : null)
  const nativeBack = useBackButton(back)

  return (
    <main className="screen">
      {back && !nativeBack && (
        <button type="button" className="back-link" onClick={back}>
          <span aria-hidden="true">‹</span> {t('back')}
        </button>
      )}
      {title && (
        <header className="screen-head">
          <h1>{title}</h1>
          {subtitle && <p className="screen-sub">{subtitle}</p>}
        </header>
      )}
      {children}
    </main>
  )
}

export function Section({ title, footer, children }) {
  return (
    <section className="section">
      {title && <h2 className="section-title">{title}</h2>}
      <div className="section-body">{children}</div>
      {footer && <p className="section-footer">{footer}</p>}
    </section>
  )
}

export function Row({ icon, title, subtitle, detail, after, onClick, chevron = Boolean(onClick), tone }) {
  const content = (
    <>
      {icon && <span className="row-icon">{icon}</span>}
      <span className="row-main">
        <span className={`row-title${tone ? ` tone-${tone}` : ''}`}>{title}</span>
        {subtitle && <span className="row-subtitle">{subtitle}</span>}
        {detail && <span className="row-detail">{detail}</span>}
      </span>
      {after && <span className="row-after">{after}</span>}
      {chevron && <span className="row-chevron" aria-hidden="true">›</span>}
    </>
  )
  return onClick ? (
    <button type="button" className="row row-button" onClick={onClick}>{content}</button>
  ) : (
    <div className="row">{content}</div>
  )
}

const TYPE_ICONS = { dayoff: '🏖', l4: '🤒', administration: '📄', accounting: '💰' }

export function TypeIcon({ type }) {
  return <span className={`type-icon type-${type}`} aria-hidden="true">{TYPE_ICONS[type] || '•'}</span>
}

export function StatusChip({ status }) {
  const { t } = useApp()
  return <span className={`chip chip-${status}`}>{t(`status_${status}`)}</span>
}

export function DateChips({ dates, lang, format }) {
  return (
    <span className="date-chips">
      {dates.map((iso) => <span key={iso} className="date-chip">{format(lang, iso)}</span>)}
    </span>
  )
}

export function Segmented({ value, options, onChange }) {
  return (
    <div className="segmented" role="tablist">
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          role="tab"
          aria-selected={value === option.value}
          className={value === option.value ? 'is-active' : ''}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}

export function Notice({ tone = 'info', children }) {
  if (!children) return null
  return <p className={`notice notice-${tone}`} role={tone === 'error' ? 'alert' : 'status'}>{children}</p>
}

export function EmptyState({ text, action }) {
  return (
    <div className="empty">
      <p>{text}</p>
      {action}
    </div>
  )
}

export function Loading() {
  return (
    <div className="loading" aria-busy="true">
      <span className="skeleton" />
      <span className="skeleton" />
      <span className="skeleton short" />
    </div>
  )
}

export function LoadError({ onRetry }) {
  const { t } = useApp()
  return (
    <div className="empty">
      <p>{t('errorText')}</p>
      <button type="button" className="btn btn-secondary" onClick={onRetry}>{t('retry')}</button>
    </div>
  )
}
