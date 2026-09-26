import { useEffect, useState } from 'react'

import { api } from '../api'
import { Calendar, Legend, Quota } from '../components/Calendar'
import { DateChips, EmptyState, LoadError, Loading, Notice, Row, Screen, Section, TypeIcon } from '../components/ui'
import { apiErrorText, useApp, useLoad, useScreenState } from '../context'
import { formatDay, monthName } from '../i18n'
import { MainAction, haptic } from '../telegram'

export function RegionPick({ type }) {
  const { t, nav } = useApp()
  const { data, loading, error, reload } = useLoad(api.regions, [])
  const regions = data?.regions || []

  // Якщо регіон лише один — одразу переходимо до вибору проєкту.
  useEffect(() => {
    if (regions.length === 1) nav.replace('projectPick', { type, region: regions[0] })
  }, [regions, nav, type])

  return (
    <Screen title={t('chooseRegion')}>
      {loading && <Loading />}
      {error && <LoadError onRetry={reload} />}
      {!loading && !error && regions.length === 0 && <EmptyState text={t('noProjects')} />}
      {regions.length > 1 && (
        <Section>
          {regions.map((region) => (
            <Row
              key={region.id}
              title={region.name}
              subtitle={t('projectsCount', { n: region.projects.length })}
              onClick={() => {
                haptic.select()
                nav.push('projectPick', { type, region })
              }}
            />
          ))}
        </Section>
      )}
    </Screen>
  )
}

export function ProjectPick({ type, region }) {
  const { t, nav } = useApp()
  return (
    <Screen title={t('chooseProject')} subtitle={region.name}>
      <Section>
        {region.projects.map((project) => (
          <Row
            key={project.id}
            title={project.name}
            onClick={() => {
              haptic.select()
              nav.push('datePick', { type, region, project })
            }}
          />
        ))}
      </Section>
    </Screen>
  )
}

const pad = (n) => String(n).padStart(2, '0')

export function DatePick({ type, region, project }) {
  const { t, lang, nav } = useApp()
  const now = new Date()
  const [cursor, setCursor] = useScreenState('cursor', { year: now.getFullYear(), month: now.getMonth() + 1 })
  const [selected, setSelected] = useScreenState('selected', [])
  const [notice, setNotice] = useState('')

  const { data, error, reload } = useLoad(
    () => api.calendar(project.id, type, cursor.year, cursor.month),
    [project.id, type, cursor.year, cursor.month],
  )
  const loadedForCursor = data && data.year === cursor.year && data.month === cursor.month
  const monthPrefix = `${cursor.year}-${pad(cursor.month)}`
  const selectedInMonth = selected.filter((iso) => iso.startsWith(monthPrefix)).length
  const canPrev = cursor.year > now.getFullYear() || (cursor.year === now.getFullYear() && cursor.month > now.getMonth() + 1)

  const shiftMonth = (delta) => {
    setNotice('')
    setCursor((current) => {
      const date = new Date(current.year, current.month - 1 + delta, 1)
      return { year: date.getFullYear(), month: date.getMonth() + 1 }
    })
  }

  const onDayClick = (iso, state) => {
    if (state === 'full') {
      haptic.error()
      setNotice(t('dayFull', { date: formatDay(lang, iso) }))
      return
    }
    if (state === 'mine') {
      haptic.error()
      setNotice(t('dayMine', { date: formatDay(lang, iso) }))
      return
    }
    if (selected.includes(iso)) {
      haptic.select()
      setNotice('')
      setSelected((current) => current.filter((item) => item !== iso))
      return
    }
    if (type === 'dayoff' && data.used_in_month + selectedInMonth >= data.limit) {
      haptic.error()
      setNotice(t('monthLimitReached', { month: monthName(lang, cursor.month, { inSentence: true }), limit: data.limit }))
      return
    }
    if (type === 'l4' && selected.length >= data.limit) {
      haptic.error()
      setNotice(t('l4LimitReached', { limit: data.limit }))
      return
    }
    haptic.select()
    setNotice('')
    setSelected((current) => [...current, iso].sort())
  }

  let quota = null
  if (loadedForCursor) {
    quota = type === 'dayoff' ? (
      <Quota
        limit={data.limit}
        used={Math.min(data.used_in_month, data.limit)}
        selected={selectedInMonth}
        label={t('quotaMonth', {
          month: monthName(lang, cursor.month),
          count: data.used_in_month + selectedInMonth,
          limit: data.limit,
        })}
      />
    ) : (
      <Quota limit={data.limit} used={0} selected={selected.length} label={t('quotaL4', { count: selected.length, limit: data.limit })} />
    )
  }

  return (
    <Screen title={t('pickDates')} subtitle={`${project.name}, ${region.name}`}>
      <div className="calendar-card">
        {quota}
        {error ? (
          <LoadError onRetry={reload} />
        ) : (
          <Calendar
            lang={lang}
            year={cursor.year}
            month={cursor.month}
            days={loadedForCursor ? data.days : null}
            today={data?.today}
            selected={selected}
            canPrev={canPrev}
            onPrev={() => shiftMonth(-1)}
            onNext={() => shiftMonth(1)}
            onDayClick={onDayClick}
          />
        )}
        <Legend t={t} type={type} />
      </div>
      <Notice tone="warning">{notice}</Notice>

      <MainAction
        text={selected.length ? t('continueCount', { n: selected.length }) : t('continue')}
        disabled={selected.length === 0}
        onClick={() => nav.push('absenceConfirm', { type, region, project, dates: selected })}
      />
    </Screen>
  )
}

export function AbsenceConfirm({ type, region, project, dates }) {
  const { t, lang, nav, reloadMe } = useApp()
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    setSending(true)
    setError('')
    try {
      await api.createAbsence({ type, project_id: project.id, dates })
      haptic.success()
      nav.reset(['home'], ['sent', { kind: 'absence' }])
    } catch (err) {
      haptic.error()
      if (err.code === 'no_access') {
        reloadMe()
        return
      }
      setError(apiErrorText(t, lang, err))
      setSending(false)
    }
  }

  return (
    <Screen title={t('confirmTitle')}>
      <Section>
        <Row icon={<TypeIcon type={type} />} title={t(`type_${type}`)} subtitle={t('fieldType')} />
        <Row title={project.name} subtitle={`${t('fieldProject')}, ${region.name}`} />
      </Section>
      <Section title={`${t('fieldDates')}: ${dates.length}`}>
        <div className="section-pad">
          <DateChips dates={dates} lang={lang} format={formatDay} />
        </div>
      </Section>
      <Notice tone="error">{error}</Notice>
      <MainAction text={t('send')} loading={sending} onClick={submit} />
    </Screen>
  )
}
