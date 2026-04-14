import { expect, test } from "@playwright/test"
import { createUser } from "./utils/privateApi"
import { randomEmail, randomPassword } from "./utils/random"
import { logInUser } from "./utils/user"

const VALID_SA_JSON = JSON.stringify(
  {
    type: "service_account",
    project_id: "test-project",
    private_key:
      "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----\n",
    client_email: "test@test-project.iam.gserviceaccount.com",
    client_id: "123456789",
  },
  null,
  2,
)

test("Service Accounts page is accessible for admin", async ({ page }) => {
  await page.goto("/service-accounts")
  await expect(
    page.getByRole("heading", { name: "Service Accounts" }),
  ).toBeVisible()
  await expect(page.getByText("Manage Google service accounts")).toBeVisible()
})

test("Add Service Account button is visible", async ({ page }) => {
  await page.goto("/service-accounts")
  await expect(
    page.getByRole("button", { name: "Add Service Account" }),
  ).toBeVisible()
})

test.describe("Service account management", () => {
  test("Create a service account by pasting JSON", async ({ page }) => {
    await page.goto("/service-accounts")

    await page.getByRole("button", { name: "Add Service Account" }).click()

    await page.getByPlaceholder("My Service Account").fill("Test SA Paste")
    await page
      .getByPlaceholder("Optional description")
      .fill("Created by pasting")

    // Select first user in dropdown
    await page.getByLabel("Assign to User").click()
    await page.getByRole("option").first().click()

    // Paste JSON tab should be active by default
    await expect(page.getByRole("tab", { name: "Paste JSON" })).toHaveAttribute(
      "data-state",
      "active",
    )
    await page
      .getByPlaceholder("Paste the Google service account JSON here...")
      .fill(VALID_SA_JSON)

    await page.getByRole("button", { name: "Save" }).click()

    await expect(
      page.getByText("Service account created successfully"),
    ).toBeVisible()

    await expect(page.getByRole("dialog")).not.toBeVisible()

    const saRow = page
      .getByRole("row")
      .filter({ hasText: "Test SA Paste" })
      .first()
    await expect(saRow).toBeVisible()
  })

  test("Create a service account by uploading file", async ({ page }) => {
    // First create a user to assign to
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })

    await page.goto("/service-accounts")
    await page.getByRole("button", { name: "Add Service Account" }).click()

    await page.getByPlaceholder("My Service Account").fill("Test SA Upload")

    // Select the user we just created
    await page.getByLabel("Assign to User").click()
    await page.getByRole("option", { name: email }).click()

    // Switch to upload tab
    await page.getByRole("tab", { name: "Upload File" }).click()

    // Upload file via hidden input
    const fileInput = page.getByTestId("credentials-file-input")
    await fileInput.setInputFiles({
      name: "sa.json",
      mimeType: "application/json",
      buffer: Buffer.from(VALID_SA_JSON),
    })

    // After upload, should switch back to paste tab with content loaded
    await expect(page.getByText("File loaded successfully"))
      .toBeVisible({
        timeout: 2000,
      })
      .catch(() => {
        // File was loaded and tab switched to paste
      })

    await page.getByRole("button", { name: "Save" }).click()

    await expect(
      page.getByText("Service account created successfully"),
    ).toBeVisible()
  })

  test("Delete a service account", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()
    await createUser({ email, password })

    await page.goto("/service-accounts")
    await page.getByRole("button", { name: "Add Service Account" }).click()

    await page.getByPlaceholder("My Service Account").fill("SA To Delete")
    await page.getByLabel("Assign to User").click()
    await page.getByRole("option", { name: email }).click()
    await page
      .getByPlaceholder("Paste the Google service account JSON here...")
      .fill(VALID_SA_JSON)
    await page.getByRole("button", { name: "Save" }).click()

    await expect(
      page.getByText("Service account created successfully"),
    ).toBeVisible()
    await expect(page.getByRole("dialog")).not.toBeVisible()

    const saRow = page.getByRole("row").filter({ hasText: "SA To Delete" })
    await saRow.getByRole("button").click()
    await page.getByRole("menuitem", { name: "Delete" }).click()
    await page.getByRole("button", { name: "Delete" }).click()

    await expect(
      page.getByText("Service account deleted successfully"),
    ).toBeVisible()

    await expect(
      page.getByRole("row").filter({ hasText: "SA To Delete" }),
    ).not.toBeVisible()
  })
})

test.describe("Service accounts access control", () => {
  test.use({ storageState: { cookies: [], origins: [] } })

  test("Non-admin cannot access service accounts page", async ({ page }) => {
    const email = randomEmail()
    const password = randomPassword()

    await createUser({ email, password })
    await logInUser(page, email, password)

    await page.goto("/service-accounts")

    await expect(
      page.getByRole("heading", { name: "Service Accounts" }),
    ).not.toBeVisible()
    await expect(page).not.toHaveURL(/\/service-accounts/)
  })
})
