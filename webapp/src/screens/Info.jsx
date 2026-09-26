import { api } from '../api'
import { EmptyState, LoadError, Loading, Row, Screen, Section } from '../components/ui'
import { useApp, useLoad } from '../context'
import { LANGUAGES } from '../i18n'
import { haptic } from '../telegram'

export function Contacts() {
  const { t } = useApp()
  const { data, loading, error, reload } = useLoad(api.coordinators, [])
  const regions = data?.regions || []

  return (
    <Screen title={t('contacts')}>
      {loading && !data && <Loading />}
      {error && <LoadError onRetry={reload} />}
      {data && regions.length === 0 && <EmptyState text={t('contactsEmpty')} />}
      {regions.map((region) => (
        <Section key={region.region} title={region.region}>
          {region.people.map((person) => (
            <Row
              key={`${region.region}-${person.name}`}
              title={person.name}
              subtitle={person.phone ? <a href={`tel:${person.phone.replace(/\s+/g, '')}`}>{person.phone}</a> : null}
              detail={person.email ? <a href={`mailto:${person.email}`}>{person.email}</a> : null}
            />
          ))}
        </Section>
      ))}
    </Screen>
  )
}

export function Language() {
  const { t, lang, nav, changeLanguage } = useApp()

  return (
    <Screen title={t('language')}>
      <Section>
        {LANGUAGES.map((item) => (
          <Row
            key={item.code}
            title={item.name}
            after={item.code === lang ? <span className="check" aria-label="✓">✓</span> : null}
            chevron={false}
            onClick={() => {
              haptic.select()
              changeLanguage(item.code)
              nav.pop()
            }}
          />
        ))}
      </Section>
    </Screen>
  )
}
