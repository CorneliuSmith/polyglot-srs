import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import WhatsNewPanel from '../features/announcements/WhatsNewPanel'
import { WHATS_NEW, unseenWhatsNew } from '../features/announcements/whatsNew'
import { usePrefsStore } from '../stores/prefsStore'

describe('unseenWhatsNew', () => {
  it('everything is unseen for a fresh account', () => {
    expect(unseenWhatsNew([])).toHaveLength(WHATS_NEW.length)
    expect(unseenWhatsNew(undefined)).toHaveLength(WHATS_NEW.length)
  })

  it('seen ids drop out of the count', () => {
    const first = WHATS_NEW[0].id
    expect(unseenWhatsNew([first])).toHaveLength(WHATS_NEW.length - 1)
    expect(unseenWhatsNew(WHATS_NEW.map((e) => e.id))).toHaveLength(0)
  })

  it('unknown seen ids (removed entries) are harmless', () => {
    expect(unseenWhatsNew(['retired-entry-2025'])).toHaveLength(WHATS_NEW.length)
  })
})

describe('WhatsNewPanel', () => {
  beforeEach(() => {
    usePrefsStore.setState({ whatsNewSeen: [] })
  })

  function renderPanel(onClose = vi.fn()) {
    render(
      <MemoryRouter>
        <WhatsNewPanel onClose={onClose} />
      </MemoryRouter>,
    )
    return onClose
  }

  it('lists every entry and marks them all seen on open', () => {
    renderPanel()
    expect(screen.getAllByTestId('whats-new-entry')).toHaveLength(
      WHATS_NEW.length,
    )
    expect(usePrefsStore.getState().whatsNewSeen).toEqual(
      expect.arrayContaining(WHATS_NEW.map((e) => e.id)),
    )
  })

  it('chips reflect what was unseen at open, not the instant mark-seen', () => {
    usePrefsStore.setState({ whatsNewSeen: [WHATS_NEW[0].id] })
    renderPanel()
    // One previously-seen entry -> one fewer "new" chip; the rest keep
    // theirs even though the store now says everything is seen.
    expect(screen.getAllByText('new')).toHaveLength(WHATS_NEW.length - 1)
  })

  it('the close button closes', () => {
    const onClose = renderPanel()
    fireEvent.click(screen.getByLabelText("Close what's new"))
    expect(onClose).toHaveBeenCalled()
  })

  it('a try-it link closes the panel (navigation happens via router)', () => {
    const withLink = WHATS_NEW.find((e) => e.link)
    expect(withLink).toBeDefined()
    const onClose = renderPanel()
    fireEvent.click(
      screen.getByRole('button', { name: new RegExp(withLink!.linkLabel!, 'i') }),
    )
    expect(onClose).toHaveBeenCalled()
  })
})
