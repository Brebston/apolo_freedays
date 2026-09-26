import { Row, Screen, Section, TypeIcon } from '../components/ui'
import { useApp } from '../context'
import { MainAction, haptic } from '../telegram'

const ABSENCE_TYPES = ['dayoff', 'l4']
const SERVICE_TYPES = ['administration', 'accounting']

export function NewRequest() {
  const { t, nav } = useApp()

  const choose = (type) => {
    haptic.select()
    if (ABSENCE_TYPES.includes(type)) nav.push('regionPick', { type })
    else nav.push('serviceText', { type })
  }

  const renderRow = (type) => (
    <Row
      key={type}
      icon={<TypeIcon type={type} />}
      title={t(`type_${type}`)}
      subtitle={t(`hint_${type}`)}
      onClick={() => choose(type)}
    />
  )

  return (
    <Screen title={t('chooseType')}>
      <Section>{ABSENCE_TYPES.map(renderRow)}</Section>
      <Section>{SERVICE_TYPES.map(renderRow)}</Section>
    </Screen>
  )
}

export function Sent({ kind, request }) {
  const { t, nav } = useApp()
  const goHome = () => nav.reset(['home'])

  return (
    <Screen onBack={goHome}>
      <div className="sent">
        <svg className="sent-mark" viewBox="0 0 64 64" width="72" height="72" aria-hidden="true">
          <circle className="sent-ring" cx="32" cy="32" r="29" />
          <path className="sent-check" d="M20 33.5l8.5 8.5L45 24" />
        </svg>
        <h1>{t('sentTitle')}</h1>
        <p className="lead">
          {kind === 'service' ? t('sentService') : request?.type === 'l4' ? t('sentL4') : t('sentAbsence')}
        </p>
        {request?.type === 'l4' && (
          <button type="button" className="btn btn-secondary" onClick={() => nav.push('sickLeave', { request })}>
            📎 {t('attachNow')}
          </button>
        )}
      </div>
      <MainAction text={t('toHome')} onClick={goHome} />
    </Screen>
  )
}
