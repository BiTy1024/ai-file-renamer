import { expect, test } from "@playwright/test"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test("Drive page is accessible for logged-in user", async ({ page }) => {
  await page.goto("/drive")
  await expect(page.getByRole("heading", { name: "Drive" })).toBeVisible()
  await expect(
    page.getByText("Browse folders and files from Google Drive"),
  ).toBeVisible()
})

test("Drive link is visible in sidebar", async ({ page }) => {
  await page.goto("/")
  await expect(page.getByRole("link", { name: "Drive" })).toBeVisible()
})

test("Drive page shows search input", async ({ page }) => {
  await page.goto("/drive")
  await expect(page.getByPlaceholder("Search folders...")).toBeVisible()
})

test.describe("Drive access control", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Unauthenticated user is redirected from drive page", async ({
    page,
  }) => {
    await page.goto("/drive")
    await expect(page).toHaveURL(/\/login/)
  })

  test("Viewer can access drive page", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/drive")
    await expect(page.getByRole("heading", { name: "Drive" })).toBeVisible()
  })

  test("Drive page shows empty state when no service account assigned", async ({
    page,
  }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/drive")
    await expect(
      page.getByText("No service account assigned to your account"),
    ).toBeVisible()
  })
})

// These tests require a real service account with folders configured.
// They are skipped in CI unless GOOGLE_SA_CREDENTIALS_JSON is available.
test.describe("Drive folder tree (requires SA with folders)", () => {
  test.fixme(
    !process.env.GOOGLE_DRIVE_TEST_FOLDER_ID,
    "Requires GOOGLE_DRIVE_TEST_FOLDER_ID - a Drive folder shared with the service account",
  )

  test("Drive page shows folder tree with root folders", async ({ page }) => {
    await page.goto("/drive")
    await expect(page.locator('[aria-label="Expand"]').first()).toBeVisible()
  })

  test("Folder tree expands subfolders on chevron click", async ({ page }) => {
    await page.goto("/drive")
    const firstChevron = page.locator('[aria-label="Expand"]').first()
    await firstChevron.click()
    // After expanding, chevron should become "Collapse"
    await expect(page.locator('[aria-label="Collapse"]').first()).toBeVisible()
  })

  test("Clicking folder in tree navigates to folder page", async ({ page }) => {
    await page.goto("/drive")
    const firstFolder = page
      .getByRole("button")
      .filter({ hasText: /\w/ })
      .first()
    await firstFolder.click()
    await expect(page).toHaveURL(/\/drive-folder\//)
  })

  test("Search returns results and clears on selection", async ({ page }) => {
    await page.goto("/drive")
    await page.getByPlaceholder("Search folders...").fill("a")
    // Wait for debounce — query fires at ≥2 chars
    await page.getByPlaceholder("Search folders...").fill("in")
    await page.waitForTimeout(400)
    // Results container should appear
    const results = page.locator("button").filter({ hasText: /\// }).first()
    await results.click()
    await expect(page).toHaveURL(/\/drive-folder\//)
    await expect(page.getByPlaceholder("Search folders...")).toHaveValue("")
  })
})
