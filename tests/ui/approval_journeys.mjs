// Shared browser assertions for the local synthetic fixtures.
export async function verifyKeyboardRejection(page, prefix, record) {
  await page.setViewportSize({ width: 768, height: 900 });
  const rows = page.locator('tbody tr');
  const snapshot = () => rows.evaluateAll(elements => Object.fromEntries(elements.map(row => [
    row.querySelector('[data-label="Invoice"] strong').textContent.trim(),
    row.querySelector('[data-label="Status"]').textContent.trim(),
  ])));
  const before = await snapshot();
  record(`${prefix}:tablet-reflow`, await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));

  await page.getByRole('button', { name: 'Load error state' }).press('Enter');
  const retry = page.getByRole('button', { name: 'Retry' });
  record(`${prefix}:keyboard-error`, await retry.isVisible());
  await retry.press('Enter');
  record(`${prefix}:keyboard-recovery`, await rows.count() === Object.keys(before).length);

  const id = 'INV-1043';
  const checkbox = page.getByRole('checkbox', { name: `Select ${id}`, exact: true });
  await checkbox.press('Space');
  record(`${prefix}:keyboard-select`, await checkbox.isChecked());
  await page.getByRole('button', { name: 'Reject selected' }).press('Enter');
  const after = await snapshot();
  record(`${prefix}:exact-rejection`, before[id] === 'pending' && after[id] === 'rejected');
  record(`${prefix}:unselected-unchanged`, Object.keys(after).length === Object.keys(before).length
    && Object.entries(before).every(([key, status]) => key === id || after[key] === status));
  record(`${prefix}:rejection-selection-cleared`, !await checkbox.isChecked());
}
