import { useState } from 'react'

import { api } from '../api'
import {
  DateChips, EmptyState, LoadError, Loading, Notice, Row, Screen, Section, Segmented, StatusChip, TypeIcon,
} from '../components/ui'
import { apiErrorText, useApp, useLoad, useScreenState } from '../context'
import { formatDay, formatRange } from '../i18n'
import { MainAction, confirmDialog, haptic } from '../telegram'

export function CoordinatorList() {
  const { t, lang, nav } = useApp()
  const [filter, setFilter] = useScreenState('filter', 'new')
  const { data, loading, error, reload } = useLoad(() => api.coordinatorRequests(filter), [filter])
  const items = data?.requests || []

  return (
    <Screen title={t('coordinatorPanel')}>
      <Segmented
        value={filter}
        onChange={(value) => {
          haptic.select()
          setFilter(value)
        }}
        options={['new', 'processed', 'all'].map((value) => ({ value, label: t(`filter_${value}`) }))}
      />

      {loading && <Loading />}
      {error && <LoadError onRetry={reload} />}
      {!loading && !error && items.length === 0 && (
        <EmptyState text={filter === 'new' ? t('coordEmpty_new') : t('coordEmpty')} />
      )}
      {!loading && items.length > 0 && (
        <Section>
          {items.map((item) => (
            <Row
              key={item.id}
              icon={<TypeIcon type={item.type} />}
              title={item.worker.name}
              subtitle={`${t(`type_${item.type}`)}, ${item.project}`}
              detail={formatRange(lang, item.start, item.end)}
              after={filter === 'new' ? null : <StatusChip status={item.status} />}
              onClick={() => nav.push('coordinatorDetail', { request: item })}
            />
          ))}
        </Section>
      )}
    </Screen>
  )
}

export function CoordinatorDetail({ request }) {
  const { t, lang, nav } = useApp()
  const [current, setCurrent] = useState(request)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const isPending = current.status === 'pending'

  const decide = async (status) => {
    const question = status === 'approved' ? 'confirmApprove' : 'confirmReject'
    if (!(await confirmDialog(t(question, { name: current.worker.name })))) return

    setBusy(true)
    setError('')
    try {
      const result = await api.decide(current.id, status)
      haptic.success()
      setCurrent(result.request)
      nav.pop()
    } catch (err) {
      haptic.error()
      setError(apiErrorText(t, lang, err))
      setBusy(false)
    }
  }

  return (
    <Screen title={current.worker.name} subtitle={`${current.project}, ${current.region}`}>
      <Section>
        <Row icon={<TypeIcon type={current.type} />} title={t(`type_${current.type}`)} subtitle={t('fieldType')} />
        <Row title={t('status')} after={<StatusChip status={current.status} />} />
        {current.worker.phone && (
          <Row
            title={<a href={`tel:${current.worker.phone.replace(/\s+/g, '')}`}>{current.worker.phone}</a>}
            subtitle={t('phone')}
          />
        )}
      </Section>

      <Section title={`${t('fieldDates')}: ${current.days}`}>
        <div className="section-pad">
          <DateChips dates={current.dates} lang={lang} format={formatDay} />
        </div>
      </Section>

      <Notice tone="error">{error}</Notice>

      {isPending && (
        <>
          {current.can_reject ? (
            <div className="secondary-action">
              <button type="button" className="btn btn-destructive" disabled={busy} onClick={() => decide('rejected')}>
                {t('reject')}
              </button>
            </div>
          ) : (
            <p className="section-footer standalone">{t('l4NoReject')}</p>
          )}
          <MainAction text={t('approve')} loading={busy} onClick={() => decide('approved')} />
        </>
      )}
    </Screen>
  )
}
