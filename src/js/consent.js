/**
 * Cookie consent banner. Analytics scripts tagged data-category="analytics" stay inert until
 * the visitor accepts that category, and Google Consent Mode is updated to match.
 */

import 'vanilla-cookieconsent/dist/cookieconsent.css'
import * as CookieConsent from 'vanilla-cookieconsent'

const syncConsentMode = () => {
  window.gtag('consent', 'update', {
    analytics_storage: CookieConsent.acceptedCategory('analytics') ? 'granted' : 'denied',
  })
}

CookieConsent.run({
  guiOptions: {
    consentModal: { layout: 'box', position: 'bottom right' },
    preferencesModal: { layout: 'box' },
  },
  categories: {
    necessary: { enabled: true, readOnly: true },
    analytics: {
      autoClear: { cookies: [{ name: /^_ga/ }, { name: '_gid' }] },
    },
  },
  onConsent: syncConsentMode,
  onChange: syncConsentMode,
  language: {
    default: 'en',
    translations: {
      en: {
        consentModal: {
          title: 'Cookies',
          description:
            'This site uses Google Analytics to see which pages get read. Nothing is set until you allow it.',
          acceptAllBtn: 'Accept',
          acceptNecessaryBtn: 'Reject',
          showPreferencesBtn: 'Settings',
        },
        preferencesModal: {
          title: 'Cookie settings',
          acceptAllBtn: 'Accept all',
          acceptNecessaryBtn: 'Reject all',
          savePreferencesBtn: 'Save',
          closeIconLabel: 'Close',
          sections: [
            {
              title: 'Necessary',
              description: 'Remembers your choice here. Always on.',
              linkedCategory: 'necessary',
            },
            {
              title: 'Analytics',
              description: 'Google Analytics and Google Tag Manager, for anonymous visit statistics.',
              linkedCategory: 'analytics',
            },
          ],
        },
      },
    },
  },
})
