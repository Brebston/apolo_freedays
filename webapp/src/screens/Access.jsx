import { useState } from 'react'

import { Loading, Row, Screen, Section } from '../components/ui'
import { copyText, useApp } from '../context'
import { LANGUAGES } from '../i18n'
import { MainAction, haptic, openTelegramLink } from '../telegram'

export function Splash() {
  return (
    <main className="screen">
      <Loading />
    </main>
  )
}

export function Outside() {
  const { t } = useApp()
  return (
    <main className="screen screen-message">
      <h1>{t('outsideTitle')}</h1>
      <p className="lead">{t('outsideText')}</p>
    </main>
  )
}

export function ErrorState({ onRetry }) {
  const { t } = useApp()
  return (
    <main className="screen screen-message">
      <h1>{t('errorTitle')}</h1>
      <p className="lead">{t('errorText')}</p>
      <button type="button" className="btn btn-secondary" onClick={onRetry}>{t('retry')}</button>
    </main>
  )
}

export function NoAccess() {
  const { t, lang, me, nav, reloadMe } = useApp()
  const [copied, setCopied] = useState(false)
  const [checking, setChecking] = useState(false)
  const telegramId = String(me.telegram_id)

  const copy = async () => {
    if (await copyText(telegramId)) {
      haptic.success()
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2000)
    }
  }

  const share = () => {
    const text = t('shareTemplate', { id: telegramId })
    openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(text)}`)
  }

  const check = async () => {
    setChecking(true)
    await reloadMe()
    setChecking(false)
  }

  return (
    <Screen>
      <div className="lock-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
          <rect x="4.5" y="10.5" width="15" height="10" rx="2.5" />
          <path d="M8 10.5V7.5a4 4 0 0 1 8 0v3" />
        </svg>
      </div>
      <header className="screen-head">
        <h1>{t('noAccessTitle')}</h1>
        <p className="screen-sub">{t('noAccessText')}</p>
      </header>

      <Section title={t('yourId')}>
        <div className="id-block">
          <span className="id-value">{telegramId}</span>
          <button type="button" className="btn btn-inline" onClick={copy}>{copied ? t('copied') : t('copy')}</button>
        </div>
      </Section>

      <Section>
        <Row title={checking ? '…' : t('checkAccess')} onClick={checking ? undefined : check} chevron={false} tone="link" />
        <Row
          title={t('language')}
          after={LANGUAGES.find((item) => item.code === lang)?.name}
          onClick={() => nav.push('language')}
        />
      </Section>

      <MainAction text={t('sendToCoordinator')} onClick={share} />
    </Screen>
  )
}
