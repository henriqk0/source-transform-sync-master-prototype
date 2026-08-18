import { expect, test } from "@playwright/test";

test("admin page requires sign-in", async ({ page }) => {
  await page.goto("/admin");
  await expect(
    page.getByRole("heading", { name: "Admin sign in" }),
  ).toBeVisible();
  await expect(page.getByLabel("Username")).toBeVisible();
});

test("admin can sign in and see sync status", async ({ page }) => {
  await page.goto("/admin");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password").fill("admin123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Admin" })).toBeVisible();
  await expect(page.getByText("Data synchronization")).toBeVisible();
});

test("wrong password shows an error", async ({ page }) => {
  await page.goto("/admin");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password").fill("wrong");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Invalid username or password")).toBeVisible();
});

test("seed on a seeded database surfaces the 409 refusal", async ({ page }) => {
  await page.goto("/admin");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password").fill("admin123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("button", { name: "Seed from source data" }).click();
  await expect(page.getByText("Database already seeded")).toBeVisible();
});

test("non-admin role is refused", async ({ page }) => {
  await page.goto("/admin");
  await page.getByLabel("Username").fill("maria");
  await page.getByLabel("Password").fill("maria123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(
    page.getByRole("heading", { name: "Admin only" }),
  ).toBeVisible();
});