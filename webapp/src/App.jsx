import { useCallback, useEffect, useMemo, useState } from 'react'

import { api } from './api'
import { AppContext, ScreenContext } from './context'
import { detectLanguage, makeT } from './i18n'
import { initTelegram, tg } from './telegram'
import { ErrorState, NoAccess, Outside, Splash } from './screens/Access'
import { AbsenceConfirm, DatePick, ProjectPick, RegionPick } from './screens/AbsenceFlow'
import { CoordinatorDetail, CoordinatorList } from './screens/Coordinator'
import { Home } from './screens/Home'
import { Contacts, Language } from './screens/Info'
import { MyRequests } from './screens/MyRequests'
import { NewRequest, Sent } from './screens/NewRequest'
import { ServiceConfirm, ServiceText } from './screens/ServiceFlow'

const SCREENS = {
  home: Home,
  noAccess: NoAccess,
  newRequest: NewRequest,
  regionPick: RegionPick,
  projectPick: ProjectPick,
  datePick: DatePick,
  absenceConfirm: AbsenceConfirm,
  serviceText: ServiceText,
  serviceConfirm: ServiceConfirm,
  sent: Sent,
  myRequests: MyRequests,
  contacts: Contacts,
  language: Language,
  coordinatorList: CoordinatorList,
  coordinatorDetail: CoordinatorDetail,
}

let nextEntryId = 1
const makeEntry = (name, props = {}) => ({ id: nextEntryId++, name, props, state: {} })

export default function App() {
  const [lang, setLang] = useState(() => detectLanguage(tg?.initDataUnsafe?.user?.language_code))
  const [session, setSession] = useState({ status: 'loading', me: null })
  const [stack, setStack] = useState(() => [makeEntry('home')])

  const loadMe = useCallback(async () => {
    setSession((current) => ({ ...current, status: 'loading' }))
    try {
      const me = await api.me()
      if (me.user?.language) setLang(me.user.language)
      const root = me.access ? 'home' : 'noAccess'
      setStack((current) => (current[0].name === root ? current : [makeEntry(root)]))
      setSession({ status: 'ready', me })
    } catch (error) {
      setSession({ status: error.status === 401 ? 'unauthorized' : 'error', me: null })
    }
  }, [])

  useEffect(() => {
    initTelegram()
    loadMe()
  }, [loadMe])

  const nav = useMemo(() => ({
    push: (name, props) => setStack((s) => [...s, makeEntry(name, props)]),
    replace: (name, props) => setStack((s) => [...s.slice(0, -1), makeEntry(name, props)]),
    pop: () => setStack((s) => (s.length > 1 ? s.slice(0, -1) : s)),
    reset: (...entries) => setStack(entries.map(([name, props]) => makeEntry(name, props))),
  }), [])

  const patchState = useCallback((entryId, key, next, initial) => {
    setStack((s) => s.map((item) => {
      if (item.id !== entryId) return item
      const current = key in item.state ? item.state[key] : initial
      const value = typeof next === 'function' ? next(current) : next
      return { ...item, state: { ...item.state, [key]: value } }
    }))
  }, [])

  const changeLanguage = useCallback(async (code) => {
    setLang(code)
    if (session.me?.access) {
      try {
        await api.setLanguage(code)
      } catch {
        // мова вже змінена локально; збереження спробуємо наступного разу
      }
    }
  }, [session.me])

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  const top = stack[stack.length - 1]
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [top.id])

  const t = useMemo(() => makeT(lang), [lang])
  const appValue = useMemo(
    () => ({ t, lang, me: session.me, nav, changeLanguage, reloadMe: loadMe }),
    [t, lang, session.me, nav, changeLanguage, loadMe],
  )
  const screenValue = useMemo(
    () => ({
      entry: top,
      canGoBack: stack.length > 1,
      patchState: (key, next, initial) => patchState(top.id, key, next, initial),
    }),
    [top, stack.length, patchState],
  )

  let content
  if (session.status === 'unauthorized') content = <Outside />
  else if (session.status === 'error') content = <ErrorState onRetry={loadMe} />
  else if (!session.me) content = <Splash />
  else {
    const Component = SCREENS[top.name] || Home
    content = (
      <ScreenContext.Provider value={screenValue}>
        <Component key={top.id} {...top.props} />
      </ScreenContext.Provider>
    )
  }

  return <AppContext.Provider value={appValue}>{content}</AppContext.Provider>
}
