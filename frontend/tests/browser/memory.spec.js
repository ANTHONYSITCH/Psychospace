import { test, expect } from '@playwright/test'
import { categoryLabel, sourceLabel } from '../../src/memory.js'

async function fillDraft(page, content) {
  const dialog = page.getByRole('dialog')
  await dialog.getByRole('button', { name: 'Continuer', exact: true }).click()
  await dialog.getByLabel('Information', { exact: true }).fill(content)
  await dialog.getByRole('button', { name: 'Continuer', exact: true }).click()
  await dialog.getByRole('radio', { name: '7', exact: true }).check()
  await dialog.getByRole('button', { name: 'Continuer', exact: true }).click()
}

test('real six memories have French labels, readable panels and keyboard access', async ({ page }) => {
  const memories = await (await page.request.get('/api/memories/ASTRO-001')).json()
  expect(memories).toHaveLength(6)
  await page.goto('/#memory')
  await expect(page.locator('.memory-fragment')).toHaveCount(memories.length)
  for (const memory of memories) {
    const fragment = page.getByRole('button', { name: `${categoryLabel(memory.category)} : ${memory.content}`, exact: true })
    await fragment.focus(); await page.keyboard.press('Enter')
    await expect(page.getByRole('dialog')).toContainText(memory.content)
    await expect(page.getByRole('dialog')).toContainText(sourceLabel(memory.source))
    await expect(page.getByRole('dialog')).toContainText(`${memory.importance} / 10`)
    await page.keyboard.press('Escape')
    await expect(fragment).toBeFocused()
  }
  await expect(page.locator('main')).not.toContainText(/MEM-00|support_preference|user_chat|Delete/)
  await page.locator('h1').click()
  await page.screenshot({ path: 'test-results/memory-desktop.png', fullPage: true })
})

test('real isolated create edit forget cycle preserves the original six memories', async ({ page }) => {
  test.skip(process.env.PSYCHOSPACE_REAL_MEMORY !== '1', 'Explicit real write cycle only')
  const before = await (await page.request.get('/api/memories/ASTRO-001')).json()
  const content = `Souvenir temporaire de démonstration ${Date.now()} : marcher quelques minutes m’aide à souffler.`
  const corrected = content.replace('quelques minutes', 'dix minutes')
  let id
  try {
    await page.goto('/#memory')
    await page.getByRole('button', { name: 'Ajouter quelque chose que PsychoSpace peut retenir' }).click()
    await page.getByLabel('Catégorie', { exact: true }).selectOption('coping_strategy')
    await fillDraft(page, content)
    const posted = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/api/memories'))
    await page.getByRole('button', { name: 'Confirmer', exact: true }).click()
    const response = await posted
    expect(response.status()).toBe(201)
    const created = await response.json(); id = created.id
    expect(created.created_at).toMatch(/^2080-04-16T/)
    await expect(page.getByRole('dialog')).toContainText('PsychoSpace l’a retenu.')
    await page.getByRole('button', { name: 'Fermer', exact: true }).click()
    await expect(page.locator('.memory-fragment')).toHaveCount(before.length + 1)
    await page.locator('.memory-fragment').filter({ hasText: content }).click()
    await page.getByRole('button', { name: 'Corriger', exact: true }).click()
    await fillDraft(page, corrected)
    await page.getByRole('button', { name: 'Confirmer', exact: true }).click()
    await expect(page.getByRole('dialog')).toContainText('C’est corrigé.')
    const afterEdit = await (await page.request.get('/api/memories/ASTRO-001')).json()
    expect(afterEdit.find(memory => memory.id === id)).toEqual({ ...created, content: corrected })
    await page.getByRole('button', { name: 'Oublier', exact: true }).click()
    await expect(page.getByRole('dialog')).toContainText(corrected)
    await page.getByRole('button', { name: 'Non, la garder' }).click()
    expect((await (await page.request.get('/api/memories/ASTRO-001')).json()).some(memory => memory.id === id)).toBeTruthy()
    await page.getByRole('button', { name: 'Oublier', exact: true }).click()
    await page.getByRole('button', { name: 'Oui, oublier' }).click()
    await expect(page.getByRole('dialog')).not.toBeVisible()
    await expect(page.locator('.memory-fragment')).toHaveCount(before.length)
    const after = await (await page.request.get('/api/memories/ASTRO-001')).json()
    expect(after).toEqual(before)
    console.log('Cycle mémoire réel : POST 201, PUT vérifié par GET, DELETE vérifié par GET ; six mémoires originales intactes ; mémoire temporaire :', id)
  } finally {
    if (id) {
      const remaining = await (await page.request.get('/api/memories/ASTRO-001')).json()
      if (remaining.some(memory => memory.id === id)) await page.request.delete(`/api/memories/${encodeURIComponent(id)}`)
    }
  }
})

test('failed POST and PUT keep the draft; DELETE waits for success and exposes failure', async ({ page }) => {
  await page.route('**/api/memories', route => route.fulfill({ status: 503, body: 'Raw error' }))
  await page.route('**/api/memories/*', route => route.request().method() === 'GET' ? route.continue() : route.fulfill({ status: 503, body: 'Raw error' }))
  await page.goto('/#memory')
  await page.getByRole('button', { name: 'Ajouter quelque chose que PsychoSpace peut retenir' }).click()
  await fillDraft(page, 'Mon brouillon conservé')
  await page.getByRole('button', { name: 'Confirmer', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveText('Je n’ai pas réussi à enregistrer cette information.')
  await expect(page.getByRole('dialog')).toContainText('Mon brouillon conservé')
  await page.getByRole('button', { name: 'Fermer', exact: true }).click()
  await page.locator('.memory-fragment').first().click()
  await page.getByRole('button', { name: 'Corriger', exact: true }).click()
  await fillDraft(page, 'Correction conservée')
  await page.getByRole('button', { name: 'Confirmer', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveText('Je n’ai pas réussi à enregistrer cette information.')
  await expect(page.getByRole('dialog')).toContainText('Correction conservée')
  await page.getByRole('button', { name: 'Fermer', exact: true }).click()
  await page.locator('.memory-fragment').first().click()
  await page.getByRole('button', { name: 'Oublier', exact: true }).click()
  let release
  const pending = new Promise(resolve => { release = resolve })
  await page.route('**/api/memories/*', async route => {
    if (route.request().method() !== 'DELETE') return route.continue()
    await pending; await route.fulfill({ status: 503, body: 'Raw error' })
  })
  await page.getByRole('button', { name: 'Oui, oublier' }).click()
  await expect(page.getByRole('button', { name: 'Oubli en cours…' })).toBeDisabled()
  await expect(page.locator('.memory-fragment')).toHaveCount(6)
  release()
  await expect(page.getByRole('alert')).toHaveText('Je n’ai pas réussi à l’oublier pour le moment.')
  await expect(page.locator('.memory-fragment')).toHaveCount(6)
  await expect(page.locator('body')).not.toContainText('Raw error')
})

test('GET failure retry, empty state and reduced motion at small widths', async ({ page }) => {
  await page.route('**/api/memories/*', route => route.fulfill({ status: 503, body: '{}' }))
  await page.goto('/#memory')
  await expect(page.getByRole('alert')).toContainText('Je n’arrive pas à retrouver tes souvenirs pour le moment.')
  await page.route('**/api/memories/*', route => route.fulfill({ json: [] }))
  await page.getByRole('button', { name: 'Réessayer' }).click()
  await expect(page.getByText('PsychoSpace ne garde encore rien de personnel ici.')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Ajouter un premier souvenir' })).toBeVisible()
  await page.unroute('**/api/memories/*')
  await page.emulateMedia({ reducedMotion: 'reduce' })
  for (const width of [768, 390]) {
    await page.setViewportSize({ width, height: 1000 })
    await page.reload()
    await expect(page.locator('.memory-fragment')).toHaveCount(6)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
    expect(await page.locator('.memory-page .presence-body').evaluate(el => getComputedStyle(el).animationName)).toBe('none')
    await page.screenshot({ path: `test-results/memory-${width}.png`, fullPage: true })
    await page.locator('.memory-fragment').first().click()
    await expect(page.getByRole('button', { name: 'Corriger', exact: true })).toBeVisible()
    await page.keyboard.press('Escape')
  }
})
