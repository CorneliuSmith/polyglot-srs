import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getProfile } from '../api/profile'
import { usePrefsStore } from '../stores/prefsStore'
import { applyUiSkin, DEFAULT_SKIN } from '../lib/uiSkin'

/**
 * Puts the account on the visual direction the server assigned it.
 *
 * Signed out, or before the profile lands, the app stays on whatever the
 * inline script in index.html painted — the last skin this browser saw, or
 * Classic. When the profile arrives the server's answer wins and is cached
 * for the next first frame.
 *
 * Deliberately re-applied on every profile load rather than once: an admin
 * turning an experiment off has to reach people on their next page, not
 * whenever they happen to clear a cache.
 */
export default function UiSkinApplier() {
  const setUiSkin = usePrefsStore((s) => s.setUiSkin)

  const { data: profile } = useQuery({
    queryKey: ['profile'],
    queryFn: getProfile,
    retry: false,
  })

  // A server that has no experiments (migration not applied, or none
  // running) sends no key at all. That must read as Classic, not as "leave
  // whatever was there" — otherwise switching an experiment off would strand
  // every browser that had already cached a variant.
  const skin = profile ? (profile.experiments?.ui_skin ?? DEFAULT_SKIN) : null

  useEffect(() => {
    if (skin === null) return
    applyUiSkin(skin)
    setUiSkin(skin === DEFAULT_SKIN ? null : skin)
  }, [skin, setUiSkin])

  return null
}
