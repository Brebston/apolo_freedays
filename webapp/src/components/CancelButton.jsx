import { useState } from 'react'

import { api } from '../api'
import { apiErrorText, useApp } from '../context'
import { confirmDialog, haptic } from '../telegram'
import { Notice } from './ui'

/** Скасування власної заявки з підтвердженням; onCancelled отримує оновлену заявку. */
export function CancelButton({ item, onCancelled }) {
  const { t, lang } = useApp()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  if (!item.can_cancel) return null

  const cancel = async () => {
    if (!(await confirmDialog(t('confirmCancel')))) return
    setBusy(true)
    setError('')
    try {
      const result = await api.cancelRequest(item.kind, item.id)
      haptic.success()
      onCancelled(result.request)
    } catch (err) {
      haptic.error()
      setError(apiErrorText(t, lang, err))
      setBusy(false)
    }
  }

  return (
    <>
      <button type="button" className="btn btn-destructive btn-cancel" disabled={busy} onClick={cancel}>
        {busy ? '…' : t('cancelRequest')}
      </button>
      <Notice tone="error">{error}</Notice>
    </>
  )
}
