import { tg } from './telegram'

export class ApiError extends Error {
  constructor(status, code, detail = {}) {
    super(code)
    this.status = status
    this.code = code
    this.detail = detail
  }
}

async function request(path, { method = 'GET', body } = {}) {
  let response
  try {
    response = await fetch(`/api${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': tg?.initData || '',
      },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'network')
  }

  let data = {}
  try {
    data = await response.json()
  } catch {
    // тіло відповіді може бути порожнім
  }
  if (!response.ok) throw new ApiError(response.status, data.error || `http_${response.status}`, data.detail)
  return data
}

/** Завантаження файлів з прогресом (fetch не повідомляє про прогрес відправки). */
function upload(path, files, onProgress) {
  return new Promise((resolve, reject) => {
    const form = new FormData()
    files.forEach((file) => form.append('files', file, file.name))
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `/api${path}`)
    xhr.setRequestHeader('X-Telegram-Init-Data', tg?.initData || '')
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress?.(Math.round((event.loaded / event.total) * 100))
    }
    xhr.onload = () => {
      let data = {}
      try {
        data = JSON.parse(xhr.responseText || '{}')
      } catch {
        // порожня або не-JSON відповідь
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data)
      else reject(new ApiError(xhr.status, data.error || `http_${xhr.status}`, data.detail))
    }
    xhr.onerror = () => reject(new ApiError(0, 'network'))
    xhr.send(form)
  })
}

export const api = {
  me: () => request('/me/'),
  setLanguage: (language) => request('/me/language/', { method: 'POST', body: { language } }),
  regions: () => request('/regions/'),
  coordinators: () => request('/coordinators/'),
  calendar: (projectId, type, year, month) =>
    request(`/projects/${projectId}/calendar/?type=${type}&year=${year}&month=${month}`),
  createAbsence: (payload) => request('/absence-requests/', { method: 'POST', body: payload }),
  createService: (payload) => request('/service-requests/', { method: 'POST', body: payload }),
  myRequests: () => request('/my-requests/'),
  coordinatorRequests: (filter) => request(`/coordinator/requests/?filter=${filter}`),
  uploadSickLeave: (requestId, files, onProgress) => upload(`/absence-requests/${requestId}/documents/`, files, onProgress),
  decide: (id, status) => request(`/coordinator/requests/${id}/decide/`, { method: 'POST', body: { status } }),
}
