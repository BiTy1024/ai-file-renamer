import { expect, test } from "@playwright/test"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test("Usage page is accessible for admin", async ({ page }) => {
  await page.goto("/usage")
  await expect(
    page.getByRole("heading", { name: "Usage & Limits" }),
  ).toBeVisible()
  await expect(
    page.getByText("Monitor API usage and manage rate limits"),
  ).toBeVisible()
})

test("Usage page shows user table", async ({ page }) => {
  await page.goto("/usage")
  await expect(page.getByRole("columnheader", { name: "User" })).toBeVisible()
  await expect(
    page.getByRole("columnheader", { name: "Requests Today" }),
  ).toBeVisible()
})

test.describe("Usage access control", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Non-admin cannot access usage page", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/usage")
    await expect(
      page.getByRole("heading", { name: "Usage & Limits" }),
    ).not.toBeVisible()
    await expect(page).not.toHaveURL(/\/usage/)
  })

  test("Normal user sees My Usage card on home page", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await expect(page.getByText("My Usage")).toBeVisible()
  })
})
