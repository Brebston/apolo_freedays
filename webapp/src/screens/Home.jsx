import { Row, Screen, Section, StatusChip, TypeIcon } from '../components/ui'
import { useApp, useLoad } from '../context'
import { LANGUAGES, formatRange, monthName } from '../i18n'
import { api } from '../api'
import { haptic } from '../telegram'

export function requestSummary(t, lang, item) {
  if (item.kind === 'absence') return `${formatRange(lang, item.start, item.end)}, ${item.project}`
  return item.text.length > 70 ? `${item.text.slice(0, 67)}…` : item.text
}

export function Home() {
  const { t, lang, me, nav } = useApp()
  const requests = useLoad(api.myRequests, [])
  const balance = useLoad(api.balance, [])
  const pending = useLoad(
    () => (me.user.is_staff ? api.coordinatorRequests('new') : Promise.resolve({ requests: [] })),
    [],
  )
  const latest = requests.data?.requests?.[0]
  const missingSickNotes = (requests.data?.requests || [])
    .filter((item) => item.type === 'l4' && item.needs_document && !['rejected', 'cancelled'].includes(item.status))
    .slice(0, 3)
  const newCount = pending.data?.requests?.length || 0

  return (
    <Screen>
      <header className="screen-head home-head">
        <h1>{t('hello', { name: me.user.first_name })}</h1>
      </header>

      <button
        type="button"
        className="hero-action"
        onClick={() => {
          haptic.tap()
          nav.push('newRequest')
        }}
      >
        <span className="hero-plus" aria-hidden="true">+</span>
        <span className="hero-text">
          <span className="hero-title">{t('newRequest')}</span>
          <span className="hero-hint">{t('newRequestHint')}</span>
        </span>
      </button>

      {(balance.data?.projects || []).map((project) => (
        <Section key={project.project_id} title={`${t('balanceTitle')}: ${project.project}`}>
          {project.months.map((m) => {
            const left = Math.max(m.limit - m.used, 0)
            return (
              <div key={`${m.year}-${m.month}`} className="balance-row">
                <div className="balance-text">
                  <span className="row-title">{monthName(lang, m.month)}</span>
                  <span className="row-subtitle">{t('balanceUsed', { used: m.used, limit: m.limit })}</span>
                </div>
                <div className="balance-side">
                  {m.limit <= 15 && (
                    <span className="quota-pips balance-pips" aria-hidden="true">
                      {Array.from({ length: m.limit }, (_, i) => (
                        <span key={i} className={`pip${i < m.used ? ' pip-used' : ''}`} />
                      ))}
                    </span>
                  )}
                  <span className={`balance-left${left === 0 ? ' is-empty' : ''}`}>{t('balanceLeft', { n: left })}</span>
                </div>
              </div>
            )
          })}
        </Section>
      ))}

      {missingSickNotes.length > 0 && (
        <Section title={t('homeReminderTitle')}>
          {missingSickNotes.map((item) => (
            <Row
              key={item.id}
              icon={<span className="type-icon type-attention" aria-hidden="true">📎</span>}
              title={t('attachSickLeave')}
              subtitle={requestSummary(t, lang, item)}
              onClick={() => nav.push('sickLeave', { request: item })}
            />
          ))}
        </Section>
      )}

      {latest && (
        <Section title={t('latest')}>
          <Row
            icon={<TypeIcon type={latest.type} />}
            title={t(`type_${latest.type}`)}
            subtitle={requestSummary(t, lang, latest)}
            after={<StatusChip status={latest.status} />}
            onClick={() => nav.push('myRequests')}
            chevron={false}
          />
        </Section>
      )}

      <Section>
        <Row title={t('myRequests')} onClick={() => nav.push('myRequests')} />
        <Row title={t('contacts')} onClick={() => nav.push('contacts')} />
        {me.user.is_staff && (
          <Row
            title={t('coordinatorPanel')}
            after={newCount > 0 ? <span className="badge">{t('newCount', { n: newCount })}</span> : null}
            onClick={() => nav.push('coordinatorList')}
          />
        )}
        <Row
          title={t('language')}
          after={LANGUAGES.find((item) => item.code === lang)?.name}
          onClick={() => nav.push('language')}
        />
      </Section>
    </Screen>
  )
}
