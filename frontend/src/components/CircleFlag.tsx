import { Globe } from 'lucide-react'
import adFlag from '../assets/flags/ad.svg'
import brFlag from '../assets/flags/br.svg'
import deFlag from '../assets/flags/de.svg'
import esFlag from '../assets/flags/es.svg'
import frFlag from '../assets/flags/fr.svg'
import gbFlag from '../assets/flags/gb.svg'
import grFlag from '../assets/flags/gr.svg'
import inFlag from '../assets/flags/in.svg'
import itFlag from '../assets/flags/it.svg'
import jmFlag from '../assets/flags/jm.svg'
import krFlag from '../assets/flags/kr.svg'
import neFlag from '../assets/flags/ne.svg'
import ngFlag from '../assets/flags/ng.svg'
import nlFlag from '../assets/flags/nl.svg'
import nzFlag from '../assets/flags/nz.svg'
import roFlag from '../assets/flags/ro.svg'
import ruFlag from '../assets/flags/ru.svg'
import saFlag from '../assets/flags/sa.svg'
import thFlag from '../assets/flags/th.svg'
import trFlag from '../assets/flags/tr.svg'
import tzFlag from '../assets/flags/tz.svg'
import zaFlag from '../assets/flags/za.svg'

/** Round flag per LANGUAGE code (vendored HatScripts circle-flags — see
 * assets/flags/LICENSE.md). Country choices mirror languageColors: Catalan →
 * Andorra, Portuguese → Brazil, Hausa → Niger (vs Yoruba's Nigeria), Swahili
 * → Tanzania, Arabic → Saudi Arabia, Māori → New Zealand. Unknown codes fall
 * back to a globe so the layout never breaks. */
const FLAG_BY_LANGUAGE: Record<string, string> = {
  es: esFlag,
  fr: frFlag,
  de: deFlag,
  it: itFlag,
  pt: brFlag,
  ca: adFlag,
  ro: roFlag,
  tr: trFlag,
  el: grFlag,
  ru: ruFlag,
  ar: saFlag,
  en: gbFlag,
  sw: tzFlag,
  yo: ngFlag,
  ha: neFlag,
  xh: zaFlag,
  mi: nzFlag,
  jam: jmFlag,
  nl: nlFlag,
  hi: inFlag,
  th: thFlag,
  ko: krFlag,
}

export default function CircleFlag({
  code,
  size = 20,
  className = '',
}: {
  code: string | undefined | null
  size?: number
  className?: string
}) {
  const src = code ? FLAG_BY_LANGUAGE[code] : undefined
  if (!src) {
    return (
      <Globe
        aria-hidden
        className={`shrink-0 text-gray-400 ${className}`}
        style={{ width: size, height: size }}
      />
    )
  }
  return (
    <img
      src={src}
      alt=""
      aria-hidden
      width={size}
      height={size}
      data-testid={`flag-${code}`}
      className={`shrink-0 rounded-full ${className}`}
    />
  )
}
