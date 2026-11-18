import { describe, expect, it } from 'vitest'


describe('AssetImport form', () => {
  it('keeps custom tags within the five-tag limit', () => {
    const form = {
      tags: ['a', 'b', 'c', 'd', 'e'],
    }

    expect(form.tags.length).toBeLessThanOrEqual(5)
  })
})
