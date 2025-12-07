import { describe, it, expect } from 'vitest'

describe('Test Setup', () => {
  it('should run tests successfully', () => {
    expect(1 + 1).toBe(2)
  })

  it('should have access to DOM matchers', () => {
    const element = document.createElement('div')
    element.textContent = 'Hello'
    document.body.appendChild(element)
    expect(element).toBeInTheDocument()
    document.body.removeChild(element)
  })
})
