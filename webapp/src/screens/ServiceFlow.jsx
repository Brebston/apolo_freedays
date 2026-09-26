import { useState } from 'react'

import { api } from '../api'
import { Notice, Row, Screen, Section, TypeIcon } from '../components/ui'
import { apiErrorText, useApp, useScreenState } from '../context'
import { MainAction, haptic } from '../telegram'

const MAX_LENGTH = 2000

export function ServiceText({ type }) {
  const { t, nav } = useApp()
  const [text, setText] = useScreenState('text', '')
  const trimmed = text.trim()

  return (
    <Screen title={t(`prompt_${type}`)} subtitle={t(`type_${type}`)}>
      <div className="field">
        <textarea
          className="textarea"
          value={text}
          maxLength={MAX_LENGTH}
          rows={7}
          placeholder={t(`placeholder_${type}`)}
          onChange={(event) => setText(event.target.value)}
          autoFocus
        />
        <span className="field-counter">{text.length}/{MAX_LENGTH}</span>
      </div>
      <MainAction
        text={t('continue')}
        disabled={!trimmed}
        onClick={() => {
          haptic.tap()
          nav.push('serviceConfirm', { type, text: trimmed })
        }}
      />
    </Screen>
  )
}

export function ServiceConfirm({ type, text }) {
  const { t, lang, nav, reloadMe } = useApp()
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  const submit = async () => {
    setSending(true)
    setError('')
    try {
      await api.createService({ type, text })
      haptic.success()
      nav.reset(['home'], ['sent', { kind: 'service' }])
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
      </Section>
      <Section title={t('fieldText')}>
        <p className="section-pad prose">{text}</p>
      </Section>
      <Notice tone="error">{error}</Notice>
      <MainAction text={t('send')} loading={sending} onClick={submit} />
    </Screen>
  )
}
