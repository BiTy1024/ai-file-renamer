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
})
