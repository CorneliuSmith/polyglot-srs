import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import LanguageWrapper from '../components/LanguageWrapper'

describe('LanguageWrapper', () => {
  it('sets dir="rtl" for Arabic language code', () => {
    const { container } = render(
      <LanguageWrapper languageCode="ar">
        <span>Arabic content</span>
      </LanguageWrapper>,
    )
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.getAttribute('dir')).toBe('rtl')
  })

  it('sets dir="ltr" for Russian language code', () => {
    const { container } = render(
      <LanguageWrapper languageCode="ru">
        <span>Russian content</span>
      </LanguageWrapper>,
    )
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.getAttribute('dir')).toBe('ltr')
  })

  it('sets dir="ltr" for English language code', () => {
    const { container } = render(
      <LanguageWrapper languageCode="en">
        <span>English content</span>
      </LanguageWrapper>,
    )
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.getAttribute('dir')).toBe('ltr')
  })

  it('applies Noto Naskh Arabic font class for Arabic', () => {
    const { container } = render(
      <LanguageWrapper languageCode="ar">
        <span>Arabic content</span>
      </LanguageWrapper>,
    )
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.className).toContain('Noto_Naskh_Arabic')
  })

  it('does not apply Arabic font class for non-Arabic languages', () => {
    const { container } = render(
      <LanguageWrapper languageCode="ru">
        <span>Russian content</span>
      </LanguageWrapper>,
    )
    const wrapper = container.firstChild as HTMLElement
    expect(wrapper.className).not.toContain('Noto_Naskh_Arabic')
  })

  it('renders children', () => {
    const { getByText } = render(
      <LanguageWrapper languageCode="en">
        <span>Test content</span>
      </LanguageWrapper>,
    )
    expect(getByText('Test content')).toBeDefined()
  })
})
