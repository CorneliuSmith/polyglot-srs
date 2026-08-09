import { Link } from 'react-router-dom'

/**
 * Terms of Service — a public page (no auth) linked from the login screen
 * and Settings. Written in plain language and kept honest about the beta:
 * community/AI-drafted content, AI tutor limits, and what we store.
 *
 * 2026-08-09 revision (owner: "up-to-date with more modern standards"):
 * covers what shipped since July — trial accounts with temporary
 * passwords, per-account pricing, transactional email — and adds the
 * sections modern terms are expected to carry: a named list of the
 * third-party services that process data, data rights (access, export,
 * deletion), statutory refund rights, feedback/IP, responsible security
 * disclosure, and a dispute/severability note. Still deliberately plain
 * language, not legalese.
 */

const LAST_UPDATED = 'August 9, 2026'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-base font-semibold text-gray-900">{title}</h2>
      <div className="text-sm text-gray-600 space-y-2">{children}</div>
    </section>
  )
}

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-10 space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Terms of Service</h1>
          <p className="text-sm text-gray-500 mt-1">
            PolyglotSRS · Last updated {LAST_UPDATED}
          </p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6 space-y-6">
          <Section title="1. What PolyglotSRS is">
            <p>
              PolyglotSRS is a spaced-repetition language-learning service:
              grammar and vocabulary decks, typed reviews, generated readings
              and exercises, and an optional AI tutor. By creating an account
              or using the service you agree to these terms. If you don't
              agree, don't use the service.
            </p>
            <p>
              The service is currently in <strong>beta</strong>. Features may
              change, break, or be removed, and we may need to reset or migrate
              data as the product evolves. We will avoid that wherever possible
              and tell you when it happens.
            </p>
          </Section>

          <Section title="2. Your account">
            <p>
              You need an account to study. Keep your credentials to yourself;
              you are responsible for activity under your account. You must be
              at least 13 years old (or the minimum age of digital consent in
              your country) to use the service. Tell us promptly if you think
              your account has been compromised.
            </p>
            <p>
              Accounts created for you (for example an approved trial) come
              with a <strong>temporary password</strong>. It is sent to the
              email address you gave us, and you must replace it with your own
              the first time you sign in. Until you do, treat that email like a
              key to your account.
            </p>
          </Section>

          <Section title="3. Trials and invitations">
            <p>
              Signup is currently by request or invitation. When you request
              trial access we store the email address and any note you submit,
              and use them only to decide on and process your request. Granting
              access is at our discretion; trials may be free or individually
              priced, may have usage allowances, and may end when the trial
              period or the beta does. If your request is declined or you
              change your mind, you can ask us to delete the request.
            </p>
          </Section>

          <Section title="4. Acceptable use">
            <p>
              Don't abuse the service: no attempts to break authentication or
              access other people's data, no scraping or bulk-extracting
              content, no using the AI tutor or audio generation for anything
              other than your own language study, no automated account
              creation, and no reselling access. Rate limits and usage
              allowances (for example, tutor message allowances) are part of
              the service; circumventing them is a breach of these terms.
            </p>
            <p>
              If you find a security vulnerability, please report it to us
              privately through the contact route below rather than exploiting
              or publishing it. We are grateful for responsible disclosure and
              will not pursue good-faith researchers.
            </p>
          </Section>

          <Section title="5. Learning content and accuracy">
            <p>
              Lessons, drills, and explanations are drafted with the help of AI
              and reviewed on an ongoing basis; native-speaker review is still
              in progress for parts of the catalogue, and some items are marked
              as drafts. Content may contain errors. If something looks wrong,
              use the in-app report option — corrections are part of how the
              beta improves.
            </p>
          </Section>

          <Section title="6. AI features">
            <p>
              Tutor conversations, generated exercises, readings, and
              translations are produced by AI models. They can be wrong, and
              nothing they produce is professional advice. Tutor messages are
              subject to the allowance on your plan.
            </p>
            <p>
              To provide these features, the text you submit to them (for
              example a tutor message or a sentence you ask to have explained)
              is processed by our AI provider (Anthropic's Claude API) under
              terms that do not permit it to be used for training their
              models. To keep coaching consistent between sessions, the tutor
              stores session summaries and the study notes it takes about your
              progress; these are visible to you in the app and are deleted
              with your account. Please don't share sensitive personal
              information in tutor chats.
            </p>
          </Section>

          <Section title="7. Audio">
            <p>
              Pronunciation audio is synthesized with neural text-to-speech
              voices (Microsoft Azure Speech; only the sentence being spoken is
              sent). It is generally accurate but is machine-generated and may
              occasionally mispronounce a word — where human recordings exist,
              they take precedence.
            </p>
          </Section>

          <Section title="8. Plans, billing, and refunds">
            <p>
              Paid plans are billed through Stripe; we never see your card
              details. Your price may be set individually (for example trial,
              classroom, or early-supporter pricing) — the amount you will be
              charged is always shown at checkout before you confirm.
              Subscriptions renew automatically until cancelled; you can cancel
              any time from the billing portal in Settings, and access
              continues to the end of the paid period.
            </p>
            <p>
              Prices may change — existing subscribers get notice before a
              change affects them, and an individually set price is never
              changed silently mid-subscription. Usage allowances reset on
              their stated cycle (daily or monthly) and unused allowance does
              not roll over. Nothing in these terms limits refund rights you
              have by law (for example the 14-day withdrawal right where it
              applies); beyond those, if something went wrong with a charge,
              contact us and we'll sort it out.
            </p>
          </Section>

          <Section title="9. Your content and feedback">
            <p>
              Text you bring to the service (notes, personal sentences, custom
              cards, writing samples) stays yours. You give us permission to
              store and process it to run the service — for example, generating
              cloze cards or audio from it. We don't use your content to train
              models, and we don't sell it.
            </p>
            <p>
              If you send us feedback, corrections, or suggestions (including
              through the in-app report tools), you agree we can use them to
              improve the service without owing you anything — a corrected
              translation you submit may end up helping every learner of that
              language.
            </p>
          </Section>

          <Section title="10. Our content">
            <p>
              The service's learning content, software, and design are ours or
              our licensors' and are licensed to you for personal study only —
              not for redistribution, republication, or building a competing
              catalogue. Open-source components remain under their own
              licenses.
            </p>
          </Section>

          <Section title="11. Privacy and your data">
            <p>
              To run the service we store: your email address, your study
              settings, your review history (which drives the spaced-repetition
              scheduling), your tutor conversations and the tutor's notes, and
              billing status. When something crashes we collect an error report
              limited to the technical failure, not your study content.
            </p>
            <p>These third parties process data for us, each only for its job:</p>
            <ul className="list-disc ps-5 space-y-1">
              <li>
                <strong>Supabase</strong> — hosting, authentication, and the
                database your data lives in.
              </li>
              <li>
                <strong>Stripe</strong> — payments. Card details are held by
                Stripe, never by us.
              </li>
              <li>
                <strong>Anthropic</strong> — AI features (see section 6).
              </li>
              <li>
                <strong>Microsoft Azure</strong> — speech synthesis (see
                section 7).
              </li>
              <li>
                <strong>Resend</strong> — transactional email (trial decisions,
                reminders you opt into).
              </li>
              <li>
                <strong>Sentry</strong> — crash reports.
              </li>
            </ul>
            <p>
              These providers may process data in countries other than yours.
              You can ask us at any time to see, correct, export, or delete
              the personal data we hold about you; deleting your account
              removes your personal data from the service, and we honour
              deletion regardless of where you live.
            </p>
          </Section>

          <Section title="12. Email">
            <p>
              We send transactional email you can't opt out of while you have
              an account (trial decisions, security or account notices) and
              optional study email you control entirely from Settings (review
              reminders, the weekly digest). We don't send marketing email.
            </p>
          </Section>

          <Section title="13. Termination">
            <p>
              You can stop using the service or delete your account at any
              time. We may suspend or terminate accounts that breach these
              terms, with notice where practical. If we ever discontinue the
              service, we will give reasonable notice so you can take your
              data with you.
            </p>
          </Section>

          <Section title="14. Disclaimers and liability">
            <p>
              The service is provided "as is", without warranties of any kind,
              during the beta especially. To the maximum extent permitted by
              law, our liability for any claim related to the service is
              limited to the amount you paid us in the twelve months before the
              claim. Nothing in these terms excludes or limits liability that
              cannot be excluded or limited under your local law, and nothing
              in them takes away consumer rights your local law gives you.
            </p>
          </Section>

          <Section title="15. Disputes">
            <p>
              If something goes wrong, contact us first — most problems are
              fixable in a message or two. These terms and any dispute under
              them are governed by the law of the operator's place of
              residence, except where your local consumer law necessarily
              applies instead. If any part of these terms turns out to be
              unenforceable, the rest still stands.
            </p>
          </Section>

          <Section title="16. Changes to these terms">
            <p>
              We may update these terms as the service evolves. Material
              changes will be announced in the app before they take effect;
              continuing to use the service after that means you accept the
              updated terms. The date at the top always tells you when they
              last changed.
            </p>
          </Section>

          <Section title="17. Contact">
            <p>
              Questions about these terms or your data: contact the operator
              through the in-app report option or the address on the project's
              GitHub page.
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
