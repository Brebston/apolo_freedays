import { createContext, useCallback, useContext, useEffect, useState } from 'react'

import { formatDateList, monthName } from './i18n'

export const AppContext = createContext(null)
export const ScreenContext = createContext(null)

export const useApp = () => useContext(AppContext)
export const useScreen = () => useContext(ScreenContext)

/** Стан, що переживає перехід на наступний екран і повернення назад. */
export function useScreenState(key, initial) {
  const screen = useContext(ScreenContext)
  const value = screen && key in screen.entry.state ? screen.entry.state[key] : initial
  const patch = screen?.patchState
  const setValue = useCallback((next) => patch?.(key, next, initial), [patch, key, initial])
  return [value, setValue]
}

/** Завантаження даних з API з повторною спробою. */
export function useLoad(loader, deps = []) {
  const [tick, setTick] = useState(0)
  const [state, setState] = useState({ loading: true, data: null, error: null })

  useEffect(() => {
    let alive = true
    setState((current) => ({ ...current, loading: true, error: null }))
    loader()
      .then((data) => alive && setState({ loading: false, data, error: null }))
      .catch((error) => alive && setState({ loading: false, data: null, error }))
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick])

  const reload = useCallback(() => setTick((n) => n + 1), [])
  return { ...state, reload }
}

/** Людський текст помилки API з урахуванням деталей від сервера. */
export function apiErrorText(t, lang, error) {
  const detail = error?.detail || {}
  switch (error?.code) {
    case 'month_limit': {
      const [month, year] = String(detail.month || '').split('.').map(Number)
      const label = month ? `${monthName(lang, month, { inSentence: true })} ${year}` : ''
      return t('err_month_limit', { month: label, used: detail.used, limit: detail.limit })
    }
    case 'date_full':
      return t('err_date_full', { dates: formatDateList(lang, detail.dates || []) })
    case 'already_requested':
      return t('err_already_requested', { dates: formatDateList(lang, detail.dates || []) })
    case 'past_date':
      return t('err_past_date')
    case 'l4_limit':
      return t('l4LimitReached', { limit: detail.limit })
    case 'text_too_long':
      return t('err_text_too_long', { limit: detail.limit })
    case 'already_decided':
      return t('err_already_decided')
    case 'l4_cannot_reject':
      return t('l4NoReject')
    default:
      return t('err_generic')
  }
}

export async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    const area = document.createElement('textarea')
    area.value = text
    area.setAttribute('readonly', '')
    area.style.position = 'fixed'
    area.style.opacity = '0'
    document.body.appendChild(area)
    area.select()
    const ok = document.execCommand('copy')
    document.body.removeChild(area)
    return ok
  }
}
