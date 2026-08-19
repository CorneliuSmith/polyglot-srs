/**
 * How wide a page is allowed to get.
 *
 * Two answers, because the pages want opposite things and the app was
 * giving them all the narrow one. A wide monitor showed Account as a
 * 576-pixel ribbon down the middle of 2000 pixels of empty grey, and the
 * section pages were not much better (owner: "it would be great to see
 * the sizes adjust a bit to better make use of the screen real estate on
 * computers").
 *
 * The distinction is what the page is made of:
 *
 * - **Dashboards of independent cards** — Study, Practice, Progress, More,
 *   Account. Nothing is read left-to-right across the full width; each
 *   card is its own small thing. Width here is free, and the cards pair up
 *   into columns rather than stretching, so the extra pixels buy less
 *   scrolling instead of longer lines.
 *
 * - **Anything with prose or a card to answer** — the review session, the
 *   Reader, lessons. Line length is a legibility constraint, not a habit:
 *   past roughly 75 characters the eye loses the line on the way back. So
 *   those pages are deliberately NOT widened here, and this constant is
 *   not for them.
 *
 * The ramp stops at 7xl (1280px). Beyond that a three-column dashboard
 * starts to read as a control panel rather than a study app, and the
 * cards would have to grow to fill it.
 */
export const PAGE_WIDE = 'max-w-2xl lg:max-w-5xl xl:max-w-6xl 2xl:max-w-7xl'

/**
 * A stack of independent cards that becomes two columns when there is
 * room. `items-start` so a short card does not stretch to match a tall
 * neighbour, which is what makes an unequal pair look broken rather than
 * merely unequal.
 *
 * Reading order stays top-to-bottom within a row (grid, not CSS columns):
 * on a page of settings, "the next card" should be the one beside it, not
 * one three screens down in an invisible first column.
 */
export const CARD_COLUMNS = 'grid gap-4 lg:grid-cols-2 items-start'
