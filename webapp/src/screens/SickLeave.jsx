import { useEffect, useRef, useState } from 'react'

import { api } from '../api'
import { DateChips, Notice, Row, Screen, Section, StatusChip } from '../components/ui'
import { apiErrorText, useApp, useScreenState } from '../context'
import { ACCEPT, MAX_FILE_BYTES, MAX_FILES_PER_UPLOAD, formatSize, isImage, prepareFile } from '../files'
import { formatDay, formatRange } from '../i18n'
import { MainAction, haptic } from '../telegram'

function FileThumb({ file }) {
  const [url, setUrl] = useState(null)
  useEffect(() => {
    if (!isImage(file)) return undefined
    const objectUrl = URL.createObjectURL(file)
    setUrl(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [file])
  if (isImage(file)) return url ? <img className="file-thumb" src={url} alt="" /> : <span className="file-thumb" />
  return <span className="file-thumb file-thumb-doc" aria-hidden="true">PDF</span>
}

export function SickLeave({ request: initialRequest }) {
  const { t, lang, nav } = useApp()
  const [request, setRequest] = useScreenState('request', initialRequest)
  const [files, setFiles] = useScreenState('files', [])
  const [phase, setPhase] = useState('idle') // idle | preparing | uploading | done
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState('')
  const inputRef = useRef(null)
  const documents = request.documents || []

  const addFiles = (list) => {
    setError('')
    const incoming = Array.from(list || [])
    const tooBig = incoming.find((file) => file.size > MAX_FILE_BYTES && !isImage(file))
    if (tooBig) {
      haptic.error()
      setError(t('err_file_too_large', { name: tooBig.name, limit: MAX_FILE_BYTES / (1024 * 1024) }))
      return
    }
    // Той самий файл, обраний повторно, не додаємо вдруге
    const fileKey = (file) => `${file.name}|${file.size}|${file.lastModified}`
    const seen = new Set(files.map(fileKey))
    const unique = incoming.filter((file) => {
      const key = fileKey(file)
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
    const next = [...files, ...unique]
    if (next.length > MAX_FILES_PER_UPLOAD) {
      haptic.error()
      setError(t('err_too_many_files', { limit: MAX_FILES_PER_UPLOAD }))
    } else {
      haptic.select()
    }
    setFiles(next.slice(0, MAX_FILES_PER_UPLOAD))
    setPhase('idle')
  }

  const removeFile = (index) => {
    haptic.select()
    setFiles((current) => current.filter((_, i) => i !== index))
  }

  const send = async () => {
    setError('')
    setPhase('preparing')
    try {
      const prepared = await Promise.all(files.map(prepareFile))
      const oversized = prepared.find((file) => file.size > MAX_FILE_BYTES)
      if (oversized) {
        haptic.error()
        setError(t('err_file_too_large', { name: oversized.name, limit: MAX_FILE_BYTES / (1024 * 1024) }))
        setPhase('idle')
        return
      }
      setPhase('uploading')
      setProgress(0)
      const result = await api.uploadSickLeave(request.id, prepared, setProgress)
      haptic.success()
      setRequest(result.request)
      setFiles([])
      setPhase('done')
    } catch (err) {
      haptic.error()
      setError(apiErrorText(t, lang, err))
      setPhase('idle')
    }
  }

  const busy = phase === 'preparing' || phase === 'uploading'
  let mainText = t('sendDocs', { n: files.length })
  if (phase === 'preparing') mainText = t('preparing')
  if (phase === 'uploading') mainText = t('uploading', { pct: progress })

  return (
    <Screen title={t('uploadTitle')} subtitle={`${request.project}, ${formatRange(lang, request.start, request.end)}`}>
      <Section>
        <Row title={t('status')} after={<StatusChip status={request.status} />} />
      </Section>

      <Section title={`${t('fieldDaysAbsent')}: ${request.days}`}>
        <div className="section-pad">
          <DateChips dates={request.dates} lang={lang} format={formatDay} />
        </div>
      </Section>

      {documents.length > 0 && (
        <Section title={t('sentDocs')}>
          {documents.map((doc) => (
            <Row
              key={doc.id}
              icon={<span className="file-thumb file-thumb-doc" aria-hidden="true">✓</span>}
              title={doc.filename}
              subtitle={doc.emailed_at ? t('docSent', { date: formatDay(lang, doc.emailed_at) }) : t('docSending')}
              after={formatSize(doc.size)}
            />
          ))}
        </Section>
      )}

      {phase === 'done' && <Notice tone="success">{t('uploadDone')}</Notice>}

      {files.length > 0 && (
        <Section title={t('selectedFiles')}>
          {files.map((file, index) => (
            <Row
              key={`${file.name}|${file.size}|${file.lastModified}`}
              icon={<FileThumb file={file} />}
              title={file.name}
              subtitle={formatSize(file.size)}
              after={
                busy ? null : (
                  <button type="button" className="btn btn-inline btn-inline-danger" onClick={() => removeFile(index)}>
                    {t('remove')}
                  </button>
                )
              }
            />
          ))}
          {busy && phase === 'uploading' && (
            <div className="upload-progress" aria-hidden="true">
              <span style={{ width: `${progress}%` }} />
            </div>
          )}
        </Section>
      )}

      {!busy && files.length < MAX_FILES_PER_UPLOAD && (
        <>
          <button type="button" className="picker" onClick={() => inputRef.current?.click()}>
            <span className="picker-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21.4 11.1l-8.9 8.9a5.5 5.5 0 0 1-7.8-7.8l8.9-8.9a3.7 3.7 0 0 1 5.2 5.2l-8.9 8.9a1.8 1.8 0 0 1-2.6-2.6l8.2-8.2" />
              </svg>
            </span>
            <span className="picker-text">
              <span className="picker-title">
                {documents.length || files.length ? t('attachMore') : t('pickFiles')}
              </span>
              <span className="picker-hint">{t('uploadHint')}</span>
            </span>
          </button>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            multiple
            hidden
            onChange={(event) => {
              addFiles(event.target.files)
              event.target.value = ''
            }}
          />
        </>
      )}

      <Notice tone="error">{error}</Notice>

      {files.length > 0 && <MainAction text={mainText} loading={busy} onClick={send} />}
      {files.length === 0 && phase === 'done' && <MainAction text={t('done')} onClick={nav.pop} />}
    </Screen>
  )
}
