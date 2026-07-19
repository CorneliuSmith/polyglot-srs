import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePrefsStore } from '../../stores/prefsStore'

/** Post-placement walkthrough (beta request: "nothing popped up showing
 * the tools available"). One card per area of the app, each tappable.
 * New accounts land here right after onboarding; anyone can reopen it
 * from Settings → "Show me around". */

const TOOLS: {
  route: string
  emoji: string
  name: string
  blurb: string
}[] = [
  {
    route: '/',
    emoji: '📬',
    name: 'Reviews',
    blurb:
      'Your daily queue, on the dashboard. A few minutes here every day is the whole game — each card comes back right before you would forget it.',
  },
  {
    route: '/grammar',
    emoji: '🛤️',
    name: 'Grammar Path',
    blurb:
      'The full grammar of your language, A1 to C2, in order. Read a point, then drill it in real sentences until it sticks.',
  },
  {
    route: '/tutor',
    emoji: '💬',
    name: 'AI Tutor',
    blurb:
      'Conversation practice that knows your cards. It steers toward your weak spots and can flag cards you clearly already know.',
  },
  {
    route: '/read',
    emoji: '📖',
    name: 'The Reader',
    blurb:
      'Short readings matched to your level. Tap any word to look it up and save it as a card.',
  },
  {
    route: '/letters',
    emoji: '🔤',
    name: 'Letters & Sounds',
    blurb:
      'The alphabet and pronunciation of your language, with audio for every letter and sound.',
  },
  {
    route: '/decks',
    emoji: '🗂️',
    name: 'Decks & Search',
    blurb:
      'Browse every vocabulary and grammar deck from A1 to C2, cram any set, or search for anything.',
  },
]

export default function WelcomePage() {
  const navigate = useNavigate()
  const setWalkthroughDone = usePrefsStore((s) => s.setWalkthroughDone)

  // This page IS the tour — don't also auto-open the slide modal the
  // dashboard shows to first-time accounts, or new users get two tours
  // back to back.
  useEffect(() => {
    setWalkthroughDone(true)
  }, [setWalkthroughDone])

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-xl mx-auto px-4 py-10 space-y-6">
        <header>
          <h1 className="text-2xl font-bold text-gray-900">Your toolkit</h1>
          <p className="text-sm text-gray-500">
            Everything in the app, one card each. Tap any of them to jump
            straight in — or head to your dashboard and start reviewing.
          </p>
        </header>

        <div className="space-y-3">
          {TOOLS.map((tool) => (
            <button
              key={tool.route + tool.name}
              type="button"
              onClick={() => navigate(tool.route)}
              className="w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-left hover:border-lang/50 hover:bg-lang-soft"
              style={{ minHeight: '44px' }}
            >
              <span className="flex items-start gap-3">
                <span aria-hidden className="text-xl leading-6">{tool.emoji}</span>
                <span>
                  <span className="block text-sm font-semibold text-gray-800">
                    {tool.name}
                  </span>
                  <span className="block text-xs text-gray-500">{tool.blurb}</span>
                </span>
              </span>
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => navigate('/', { replace: true })}
          className="w-full bg-lang hover:bg-lang-dark text-lang-on font-semibold rounded-xl px-6 py-3 text-sm"
          style={{ minHeight: '44px' }}
        >
          Go to your dashboard
        </button>

        <p className="text-xs text-gray-400 text-center">
          You can reopen this tour any time from Settings.
        </p>
      </div>
    </div>
  )
}
