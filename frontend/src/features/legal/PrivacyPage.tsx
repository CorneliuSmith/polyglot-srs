import { Link } from 'react-router-dom'

/**
 * Privacy Policy — a public page (no auth), the standalone companion to
 * TermsPage. Exists separately because app stores require a dedicated
 * privacy-policy URL for submission, and because "what do you do with my
 * data" deserves a page, not a section.
 *
 * Written plain and kept factually tied to what the code actually does —
 * every claim below is checkable in the repository. LEGAL REVIEW PENDING:
 * the owner's reviewer should fill/confirm the items marked with
 * "REVIEWER:" comments before public launch (entity name, governing
 * jurisdiction, contact address, EU/UK representative if needed). Until
 * then the page errs toward promising less, never more.
 */

const LAST_UPDATED = 'August 30, 2026'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-base font-semibold text-gray-900">{title}</h2>
      <div className="text-sm text-gray-600 space-y-2">{children}</div>
    </section>
  )
}

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-10 space-y-6">
        <div>
          {/* REVIEWER: replace "PolyglotSRS" with the operating entity's
              legal name + form once one exists. */}
          <h1 className="text-2xl font-bold text-gray-900">Privacy Policy</h1>
          <p className="text-sm text-gray-500 mt-1">
            PolyglotSRS · Last updated {LAST_UPDATED}
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-6">
          <Section title="1. The short version">
            <p>
              We store what the service needs to teach you a language and
              nothing else: your email, your settings, your study history, the
              content you create, and your conversations with the AI tutor. We
              don't sell data, we don't show ads, we don't use your content to
              train AI models, and your voice recordings are never stored.
              Deleting your account deletes your personal data.
            </p>
          </Section>

          <Section title="2. What we store, and why">
            <ul className="list-disc ps-5 space-y-1">
              <li>
                <strong>Account</strong> — your email address and password
                hash (held by our authentication provider), your interface
                language, and your settings. Why: signing you in and keeping
                the app the way you set it.
              </li>
              <li>
                <strong>Study history</strong> — which cards you reviewed,
                when, and how it went. Why: this <em>is</em> spaced
                repetition; the schedule is computed from it.
              </li>
              <li>
                <strong>Your content</strong> — notes, personal cards and
                decks, writing samples you submit. Why: you made it, the app
                stores it for you. It stays yours.
              </li>
              <li>
                <strong>Tutor conversations and study notes</strong> — what
                you and the AI tutor said, plus the summaries it keeps so
                coaching stays consistent between sessions. Why: continuity.
                Visible to you in the app; deleted with your account.
              </li>
              <li>
                <strong>Billing status</strong> — which plan you're on and
                whether it's active. Card details are held by Stripe, never
                by us.
              </li>
              <li>
                <strong>Usage metering</strong> — counts and durations (for
                example, how many tutor messages you used, or how many
                seconds of audio were transcribed). Why: allowances and our
                own cost accounting.
              </li>
              <li>
                <strong>Error reports</strong> — when something crashes, a
                technical report about the failure. Why: fixing it. These are
                scoped to the failure, not your study content.
              </li>
            </ul>
          </Section>

          <Section title="3. What we deliberately do NOT store">
            <ul className="list-disc ps-5 space-y-1">
              <li>
                <strong>Your voice.</strong> When you speak to the app, the
                audio is transcribed and immediately discarded — only the
                resulting text and the audio's duration are kept.
              </li>
              <li>
                <strong>Card details.</strong> Payment goes through Stripe's
                own checkout; your card never touches our servers.
              </li>
              <li>
                <strong>Tracking for advertising.</strong> There are no ad
                trackers, no analytics beacons following you across the web,
                and no data brokers.
              </li>
            </ul>
          </Section>

          <Section title="4. Who processes data for us">
            <p>
              Six providers, each only for its job, none permitted to use
              your data for their own purposes:
            </p>
            <ul className="list-disc ps-5 space-y-1">
              <li><strong>Supabase</strong> — authentication and the database your data lives in.</li>
              <li><strong>DigitalOcean</strong> — hosting for the application servers.</li>
              <li><strong>Anthropic</strong> — the AI models behind the tutor, generated readings, and exercises. Text you submit to AI features is processed under terms that do not permit training on it.</li>
              <li><strong>Microsoft Azure</strong> — speech: synthesizing pronunciation audio and transcribing what you say (see section 3 — audio is not retained).</li>
              <li><strong>Stripe</strong> — payments and billing.</li>
              <li><strong>Resend</strong> — email: account notices and the study emails you opt into.</li>
            </ul>
            <p>
              We also use <strong>Sentry</strong> for crash reports. These
              providers may process data in countries other than yours.
              {/* REVIEWER: if EU/UK users are in scope at launch, confirm
                  transfer mechanisms (SCCs/DPF status per provider) and
                  whether an Art. 27 representative is needed. */}
            </p>
          </Section>

          <Section title="5. Your rights">
            <p>
              You can ask at any time to see, correct, export, or delete the
              personal data we hold about you, and we honour these requests
              regardless of where you live. Deleting your account removes
              your personal data from the service; backups age out on a
              short, fixed cycle afterward. Some minimal records survive
              deletion where the law requires it (for example, records of
              payments).
            </p>
          </Section>

          <Section title="6. Email">
            <p>
              Account and security notices are sent as needed while you have
              an account. Study emails — review reminders, the weekly digest
              — are off until you turn them on, and every one has an off
              switch in Settings. No marketing email.
            </p>
          </Section>

          <Section title="7. Children">
            <p>
              The service is for people 13 and over (or the age of digital
              consent where you live). We don't knowingly collect data from
              children below that age; if you believe a child is using the
              service, contact us and we'll remove the account.
            </p>
          </Section>

          <Section title="8. Changes and contact">
            <p>
              If this policy changes materially, the app will say so before
              the change takes effect, and the date at the top always tells
              you when it last moved. Questions or requests about your data:
              use the in-app report option
              {/* REVIEWER: add a monitored contact email / postal address
                  here before public launch — stores and GDPR both expect
                  one. */}
              , and see also the <Link to="/terms" className="text-lang hover:underline">Terms of Service</Link>.
            </p>
          </Section>
        </div>

        <div className="text-center">
          <Link to="/" className="text-sm text-lang hover:underline">
            ← Back to PolyglotSRS
          </Link>
        </div>
      </div>
    </div>
  )
}
