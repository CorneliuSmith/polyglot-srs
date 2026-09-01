import { describe, it, expect, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import i18n from '../i18n'
import InfoDot from '../components/InfoDot'

describe('the gloss explains itself', () => {
  afterEach(() => void i18n.changeLanguage('en'))

  function renderHelp() {
    return render(
      <InfoDot
        label={i18n.t('review.glossHelpTitle')}
        title={i18n.t('review.glossHelpTitle')}
        testId="gloss-help"
      >
        {i18n.t('review.glossHelpBody')}
      </InfoDot>,
    )
  }

  it('stays out of the way until asked', () => {
    renderHelp()
    expect(screen.queryByTestId('gloss-help-body')).toBeNull()
  })

  it('decodes the notation with a worked example', () => {
    renderHelp()
    fireEvent.click(screen.getByTestId('gloss-help'))
    const body = screen.getByTestId('gloss-help-body')
    // The three things a confused learner needs: it is not a translation,
    // what the dot means, and why the labels are English.
    expect(body.textContent).toContain('not a translation')
    expect(body.textContent).toContain('bark.3SG')
    expect(body.textContent).toContain('English')
  })

  it('closes on Escape', () => {
    renderHelp()
    fireEvent.click(screen.getByTestId('gloss-help'))
    expect(screen.getByTestId('gloss-help-body')).toBeDefined()
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByTestId('gloss-help-body')).toBeNull()
  })

  it('is written in every UI locale', async () => {
    // The gloss NOTATION is English by design (owner, 2026-08-27 — the value
    // is the decomposition, so its metalanguage does not vary). The
    // EXPLANATION of that notation is exactly the thing that must not be:
    // a learner who cannot read the explanation is the learner it is for.
    for (const lng of ['en', 'es', 'fr', 'pt', 'ru', 'ar']) {
      const title = i18n.t('review.glossHelpTitle', { lng })
      const body = i18n.t('review.glossHelpBody', { lng })
      expect(title, `no title for ${lng}`).not.toBe('review.glossHelpTitle')
      expect(body, `no body for ${lng}`).not.toBe('review.glossHelpBody')
      // Long enough to actually explain rather than label.
      expect(body.length, `${lng} body is too short to explain`).toBeGreaterThan(80)
      // The worked example survives translation — it is the part that
      // teaches the notation, and it is the same in every language.
      expect(body, `${lng} lost the example`).toContain('bark.3SG')
    }
  })

  it('reads in the learner’s own language, not English', async () => {
    await i18n.changeLanguage('ru')
    renderHelp()
    fireEvent.click(screen.getByTestId('gloss-help'))
    expect(screen.getByTestId('gloss-help-body').textContent).toContain(
      'а не перевод',
    )
  })
})
