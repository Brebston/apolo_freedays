import { Row, Screen, Section, StatusChip, TypeIcon } from '../components/ui'
import { useApp, useLoad } from '../context'
import { LANGUAGES, formatRange } from '../i18n'
import { api } from '../api'
import { haptic } from '../telegram'

export function requestSummary(t, lang, item) {
  if (item.kind === 'absence') return `${formatRange(lang, item.start, item.end)}, ${item.project}`
  return item.text.length > 70 ? `${item.text.slice(0, 67)}…` : item.text
}

export function Home() {
  const { t, lang, me, nav } = useApp()
  const requests = useLoad(api.myRequests, [])
  const pending = useLoad(
    () => (me.user.is_staff ? api.coordinatorRequests('new') : Promise.resolve({ requests: [] })),
    [],
  )
  const latest = requests.data?.requests?.[0]
  const missingSickNotes = (requests.data?.requests || [])
    .filter((item) => item.type === 'l4' && item.needs_document && item.status !== 'rejected')
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
