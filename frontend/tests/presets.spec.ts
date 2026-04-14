import { expect, test } from "@playwright/test"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

test("Presets page is accessible for admin", async ({ page }) => {
  await page.goto("/presets")
  await expect(
    page.getByRole("heading", { name: "Convention Presets" }),
  ).toBeVisible()
})

test.describe("Preset management", () => {
  test("Create a preset", async ({ page }) => {
    await page.goto("/presets")

    await page.getByRole("button", { name: "Add Preset" }).click()

    await page.getByPlaceholder("Invoice Naming").fill("Test Invoice Preset")
    await page
      .getByPlaceholder("[INVOICE_DATE]_[TOTAL]_[COMPANY]")
      .fill("[DATE]_[AMOUNT]")
    await page.getByPlaceholder("invoice, contract").fill("invoice")

    await page.getByRole("button", { name: "Save" }).click()

    await expect(page.getByText("Preset created successfully")).toBeVisible()

    const row = page
      .getByRole("row")
      .filter({ hasText: "Test Invoice Preset" })
      .first()
    await expect(row).toBeVisible()
  })

  test("Delete a preset", async ({ page }) => {
    await page.goto("/presets")

    await page.getByRole("button", { name: "Add Preset" }).click()
    await page.getByPlaceholder("Invoice Naming").fill("To Delete")
    await page
      .getByPlaceholder("[INVOICE_DATE]_[TOTAL]_[COMPANY]")
      .fill("[NAME]")
    await page.getByRole("button", { name: "Save" }).click()
    await expect(page.getByText("Preset created successfully")).toBeVisible()
    await expect(page.getByRole("dialog")).not.toBeVisible()

    // Increase page size to 50 so all rows are visible regardless of accumulated test data
    const pageSizeSelect = page.getByRole("combobox")
    if (await pageSizeSelect.isVisible()) {
      await pageSizeSelect.click()
      await page.getByRole("option", { name: "50" }).click()
    }

    const row = page.getByRole("row").filter({ hasText: "To Delete" }).first()
    await row.getByRole("button").click()
    await page.getByRole("menuitem", { name: "Delete" }).click()
    await page.getByRole("button", { name: "Delete" }).click()

    await expect(page.getByText("Preset deleted successfully")).toBeVisible()
  })
})

test.describe("Presets access control", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Non-admin cannot access presets page", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/presets")
    await expect(
      page.getByRole("heading", { name: "Convention Presets" }),
    ).not.toBeVisible()
    await expect(page).not.toHaveURL(/\/presets/)
  })
})
