import { createElement, useEffect, useRef } from 'react'

export const tg = window.Telegram?.WebApp
export const inTelegram = Boolean(tg && tg.initData)

const supports = (version) => Boolean(tg?.isVersionAtLeast?.(version))

export function initTelegram() {
  if (!tg) return
  tg.ready()
  tg.expand()
  if (supports('6.1')) {
    tg.setHeaderColor('secondary_bg_color')
    tg.setBackgroundColor('secondary_bg_color')
  }
  if (supports('7.7')) tg.disableVerticalSwipes()
}

export const haptic = {
  select: () => supports('6.1') && tg.HapticFeedback.selectionChanged(),
  tap: () => supports('6.1') && tg.HapticFeedback.impactOccurred('light'),
  success: () => supports('6.1') && tg.HapticFeedback.notificationOccurred('success'),
  error: () => supports('6.1') && tg.HapticFeedback.notificationOccurred('error'),
}

export function confirmDialog(message) {
  if (inTelegram && supports('6.2')) {
    return new Promise((resolve) => tg.showConfirm(message, (ok) => resolve(Boolean(ok))))
  }
  return Promise.resolve(window.confirm(message))
}

export function openTelegramLink(url) {
  if (inTelegram) tg.openTelegramLink(url)
  else window.open(url, '_blank', 'noopener')
}

/** Системна кнопка «Назад» Telegram. Поза Telegram повертає false — тоді екран малює свою. */
export function useBackButton(onBack) {
  const handler = useRef(onBack)
  handler.current = onBack
  const enabled = Boolean(onBack)

  useEffect(() => {
    if (!inTelegram || !enabled || !supports('6.1')) return undefined
    const listener = () => handler.current?.()
    tg.BackButton.onClick(listener)
    tg.BackButton.show()
    return () => {
      tg.BackButton.offClick(listener)
      tg.BackButton.hide()
    }
  }, [enabled])

  return inTelegram && supports('6.1')
}

/**
 * Головна дія екрана. У Telegram керує нативною MainButton,
 * у звичайному браузері (розробка) малює кнопку внизу сторінки.
 */
export function MainAction({ text, onClick, disabled = false, loading = false }) {
  const handler = useRef(onClick)
  handler.current = onClick
  const state = useRef({ disabled, loading })
  state.current = { disabled, loading }

  useEffect(() => {
    if (!inTelegram) return undefined
    const button = tg.MainButton
    const listener = () => {
      if (state.current.disabled || state.current.loading) return
      handler.current?.()
    }
    button.onClick(listener)
    return () => {
      button.offClick(listener)
      button.hideProgress()
      button.hide()
    }
  }, [])

  useEffect(() => {
    if (!inTelegram) return
    const theme = tg.themeParams || {}
    const button = tg.MainButton
    button.setParams({
      text,
      is_visible: true,
      is_active: !disabled && !loading,
      color: disabled ? theme.hint_color || '#8a8f98' : theme.button_color || '#2f6fde',
      text_color: theme.button_text_color || '#ffffff',
    })
    if (loading) button.showProgress(false)
    else button.hideProgress()
  }, [text, disabled, loading])

  if (inTelegram) return null
  return createElement(
    'div',
    { className: 'main-action' },
    createElement(
      'button',
      { type: 'button', className: 'btn btn-primary', disabled: disabled || loading, onClick },
      loading ? '…' : text,
    ),
  )
}
