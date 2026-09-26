import { api } from '../api'
import { DateChips, EmptyState, LoadError, Loading, Row, Screen, Section, StatusChip, TypeIcon } from '../components/ui'
import { useApp, useLoad, useScreenState } from '../context'
import { formatDay } from '../i18n'
import { requestSummary } from './Home'

export function MyRequests() {
  const { t, lang, nav } = useApp()
  const { data, loading, error, reload } = useLoad(api.myRequests, [])
  const [openKey, setOpenKey] = useScreenState('open', null)
  const items = data?.requests || []

  return (
    <Screen title={t('myRequests')}>
      {loading && !data && <Loading />}
      {error && <LoadError onRetry={reload} />}
      {data && items.length === 0 && (
        <EmptyState
          text={t('myRequestsEmpty')}
          action={
            <button type="button" className="btn btn-secondary" onClick={() => nav.replace('newRequest')}>
              {t('newRequest')}
            </button>
          }
        />
      )}
      {items.length > 0 && (
        <Section>
          {items.map((item) => {
            const key = `${item.kind}-${item.id}`
            const isOpen = openKey === key
            if (item.type === 'l4') {
              return (
                <div key={key} className="request-item">
                  <Row
                    icon={<TypeIcon type={item.type} />}
                    title={t(`type_${item.type}`)}
                    subtitle={requestSummary(t, lang, item)}
                    detail={item.needs_document ? <span className="attach-hint">📎 {t('needsDocument')}</span> : null}
                    after={<StatusChip status={item.status} />}
                    onClick={() => nav.push('sickLeave', { request: item })}
                  />
                </div>
              )
            }
            return (
              <div key={key} className={`request-item${isOpen ? ' is-open' : ''}`}>
                <Row
                  icon={<TypeIcon type={item.type} />}
                  title={t(`type_${item.type}`)}
                  subtitle={requestSummary(t, lang, item)}
                  after={<StatusChip status={item.status} />}
                  onClick={() => setOpenKey(isOpen ? null : key)}
                  chevron={false}
                />
                {isOpen && (
                  <div className="request-details">
                    {item.kind === 'absence' ? (
                      <DateChips dates={item.dates} lang={lang} format={formatDay} />
                    ) : (
                      <p className="prose">{item.text}</p>
                    )}
                    <span className="request-meta">
                      {t('submittedOn', { date: formatDay(lang, item.created_at) })}
                    </span>
                  </div>
                )}
              </div>
            )
          })}
        </Section>
      )}
    </Screen>
  )
}
