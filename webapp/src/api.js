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
  decide: (id, status) => request(`/coordinator/requests/${id}/decide/`, { method: 'POST', body: { status } }),
}
