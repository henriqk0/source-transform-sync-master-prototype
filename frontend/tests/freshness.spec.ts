import { expect, test } from "@playwright/test";

test("admin sees freshness banner with timestamp and record counts", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password").fill("admin123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Admin" })).toBeVisible();

  await expect(page.getByText(/Data synced on .+ — 10 records/)).toBeVisible();
  await expect(page.getByText("SUCCEEDED")).toBeVisible();
  await expect(
    page.getByRole("main").getByText("Professors", { exact: true }),
  ).toBeVisible();
});

test("re-sync trigger surfaces the 409 refusal when data exists", async ({
  page,
}) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password").fill("admin123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Admin" })).toBeVisible();

  await page.getByRole("button", { name: "Seed from source data" }).click();
  await expect(page.getByText("Database already seeded")).toBeVisible();
  await expect(page.getByText(/Data synced on .+ — 10 records/)).toBeVisible();
});