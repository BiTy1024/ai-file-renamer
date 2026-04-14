import { expect, test } from "@playwright/test"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test.describe("Admin Dashboard - Usage Analytics", () => {
  test("Summary cards are visible on usage page", async ({ page }) => {
    await page.goto("/usage")
    await expect(page.getByText("Tokens This Month")).toBeVisible()
    await expect(page.getByText("Cost This Month")).toBeVisible()
    await expect(page.getByText("All-Time Tokens")).toBeVisible()
    await expect(page.getByText("All-Time Cost")).toBeVisible()
  })

  test("Usage chart renders with controls", async ({ page }) => {
    await page.goto("/usage")
    await expect(page.getByText("Usage Over Time")).toBeVisible()
    await expect(page.getByRole("tab", { name: "Tokens" })).toBeVisible()
    await expect(page.getByRole("tab", { name: "Cost" })).toBeVisible()
  })

  test("API key manager card is visible", async ({ page }) => {
    await page.goto("/usage")
    await expect(page.getByText("Claude API Key")).toBeVisible()
  })

  test("Global default limits card is visible", async ({ page }) => {
    await page.goto("/usage")
    await expect(page.getByText("Default Limits for New Users")).toBeVisible()
  })

  test("User table rows are clickable and navigate to detail", async ({
    page,
  }) => {
    await page.goto("/usage")
    // Wait for user table to load
    await expect(page.getByRole("columnheader", { name: "User" })).toBeVisible()
    // Click first user row
    const firstRow = page.getByRole("row").nth(1)
    await firstRow.click()
    await page.waitForURL(/\/usage\//, { timeout: 15000 })
    await expect(page.getByText("Current Usage")).toBeVisible({
      timeout: 15000,
    })
  })

  test("User detail page shows usage chart", async ({ page }) => {
    await page.goto("/usage")
    await expect(page.getByRole("columnheader", { name: "User" })).toBeVisible()
    const firstRow = page.getByRole("row").nth(1)
    await firstRow.click()
    await page.waitForURL(/\/usage\//, { timeout: 15000 })
    await expect(page.getByText("User Usage Over Time")).toBeVisible({
      timeout: 15000,
    })
    await expect(page.getByText("Recent Rename Operations")).toBeVisible()
  })

  test("User detail page has back button to usage page", async ({ page }) => {
    await page.goto("/usage")
    await expect(page.getByRole("columnheader", { name: "User" })).toBeVisible()
    const firstRow = page.getByRole("row").nth(1)
    await firstRow.click()
    await page.waitForURL(/\/usage\//)
    // Click back arrow
    await page
      .getByRole("link", { name: /back/i })
      .or(page.locator("a[href='/usage']"))
      .first()
      .click()
    await page.waitForURL("/usage")
  })
})

test.describe("Admin Dashboard - Activity Log", () => {
  test("Activity page is accessible", async ({ page }) => {
    await page.goto("/activity")
    await expect(
      page.getByRole("heading", { name: "Activity Log" }),
    ).toBeVisible()
  })

  test("Activity page has filter controls", async ({ page }) => {
    await page.goto("/activity")
    await expect(page.getByText("Filters")).toBeVisible()
    await expect(page.getByText("Export CSV")).toBeVisible()
  })

  test("Activity link visible in sidebar for admin", async ({ page }) => {
    await page.goto("/")
    await expect(page.getByRole("link", { name: "Activity" })).toBeVisible()
  })
})

test.describe("Admin Dashboard - Access Control", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Non-admin cannot access activity page", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/activity")
    await expect(
      page.getByRole("heading", { name: "Activity Log" }),
    ).not.toBeVisible()
    await expect(page).not.toHaveURL(/\/activity/)
  })
})

test.describe("Admin Dashboard - API Key Management", () => {
  test("Can open API key dialog", async ({ page }) => {
    await page.goto("/usage")
    await expect(page.getByText("Claude API Key")).toBeVisible()
    const setButton = page.getByRole("button", { name: /Set Key|Update Key/ })
    await setButton.click()
    await expect(
      page.getByRole("heading", { name: "Set Claude API Key" }),
    ).toBeVisible()
    await expect(page.getByPlaceholder("sk-ant-api03-...")).toBeVisible()
  })
})
