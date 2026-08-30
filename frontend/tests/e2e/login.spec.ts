import { test, expect } from '@playwright/test';

test.describe('Login Page', () => {
  test('renders login page with title and API key input', async ({ page }) => {
    const response = await page.goto('/en/login');
    expect(response?.ok()).toBe(true);

    await expect(page.locator('h1')).toContainText('zksato');
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('text=Sign In with API Key')).toBeVisible();
  });

  test('API key input is enabled', async ({ page }) => {
    await page.goto('/en/login');
    const input = page.locator('input[type="password"]');
    await expect(input).toBeVisible();
    await expect(input).toBeEnabled();
  });

  test('shows error for invalid API key', async ({ page }) => {
    await page.goto('/en/login');
    await page.route('**/v1/auth/session', async (route) => {
      await route.fulfill({ status: 401, body: '{"detail":"Invalid API key"}' });
    });
    const input = page.locator('input[type="password"]');
    await input.fill('invalid-key');
    await page.locator('button[type="submit"]').click();
    await expect(page.locator('text=Invalid API key')).toBeVisible({ timeout: 2000 });
  });

  test('stores API key in sessionStorage on success', async ({ page }) => {
    await page.goto('/en/login');
    await page.route('**/v1/auth/session', async (route) => {
      await route.fulfill({ status: 200, body: '{"subject":"test","role":"read_only","csrf_token":"tok","expires_at":"2099-01-01T00:00:00"}' });
    });
    const input = page.locator('input[type="password"]');
    await input.fill('valid-key');
    await page.locator('button[type="submit"]').click();
    await page.waitForFunction(() => sessionStorage.getItem('zksato_api_key') !== null, { timeout: 5000 });
    const key = await page.evaluate(() => sessionStorage.getItem('zksato_api_key'));
    expect(key).toBe('valid-key');
  });

  test('login page is responsive on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/en/login');
    const card = page.locator('.glass-card-static');
    const box = await card.boundingBox();
    expect(box).not.toBeNull();
    if (box) {
      expect(box.width).toBeLessThan(440);
      expect(box.height).toBeLessThan(600);
    }
    await expect(page.locator('h1')).toBeVisible();
  });
});
