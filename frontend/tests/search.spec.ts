import { expect, test } from "@playwright/test";

test("search journey: query reaches the correct profile", async ({ page }) => {
  await page.goto("/");
  const search = page.getByLabel("Search professors by name");
  await search.fill("Maria");
  await expect(
    page.getByRole("link", { name: "Maria Alice Veiga Ferreira De Souza" }),
  ).toBeVisible();

  await page
    .getByRole("link", { name: "Maria Alice Veiga Ferreira De Souza" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Maria Alice Veiga Ferreira De Souza" }),
  ).toBeVisible();
  await expect(page.getByText("Vila Velha").first()).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Current projects" }),
  ).toBeVisible();
});

test("search journey: typing narrows results and empty state appears", async ({
  page,
}) => {
  await page.goto("/");
  const search = page.getByLabel("Search professors by name");
  await search.fill("zzz-no-such-name");
  await expect(page.getByText("No professors found.")).toBeVisible();
});

test("search journey: empty query lists all professors", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("4 professors found")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Ana Paula Sem Dados" }),
  ).toBeVisible();
});