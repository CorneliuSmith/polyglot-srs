/**
 * The feature tour's edition number.
 *
 * "Don't show again" only ever meant "done with the tour as it stood that
 * day". The app has since grown a conversation partner, a level dial that
 * runs A1 → C2 and past it, a shelf you can tidy, and a tutor whose memory
 * you can read — none of which existed in the tour anyone has already
 * dismissed. The owner: *"put the necessary in the walkthrough. Force all to
 * see the new walkthrough."*
 *
 * So the dashboard compares this against `prefsStore.walkthroughVersion`
 * rather than a boolean: bump it when a slide is added or materially
 * rewritten and everyone is offered the tour once more. It is still a tour,
 * not a wall — the close button and "don't show again" work exactly as they
 * did, and dismissing writes this version so nobody is asked twice for the
 * same edition.
 *
 * 0 → the original seven-slide tour (pre-versioning; anyone who dismissed it
 *     carries walkthroughVersion 0 whatever their walkthroughDone says).
 * 1 → adds Speak, rewrites Read for the level dial and the shelf, and points
 *     at the tutor's memory panel.
 */
export const TOUR_VERSION = 1
