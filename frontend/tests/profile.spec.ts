import { expect, test } from "@playwright/test";

test.describe("Professor profile page (US1)", () => {
  test("renders hierarchical sections in order with matching data", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Maria Alice Veiga Ferreira De Souza" }).click();
    await expect(page).toHaveURL(/\/professors\/\d+/);

    await expect(
      page.getByRole("heading", { name: "Maria Alice Veiga Ferreira De Souza" }),
    ).toBeVisible();
    await expect(page.getByText("Vila Velha").first()).toBeVisible();

    const headings = page.locator("main h2");
    await expect(headings.nth(0)).toHaveText("Current projects");
    await expect(headings.nth(1)).toHaveText("Article counts by year");
    await expect(headings.nth(2)).toHaveText("Research locations");
    await expect(headings.nth(3)).toHaveText("Articles");

    await expect(page.getByText("Projeto Ativo de Maria")).toBeVisible();
    await expect(page.getByRole("cell", { name: "2025" })).toBeVisible();
    await expect(
      page
        .locator("tbody tr")
        .filter({ has: page.getByRole("cell", { name: "2025" }) })
        .getByRole("cell", { name: "1" }),
    ).toBeVisible();
    await expect(page.getByText("Publicação 2025 de Maria")).toBeVisible();
  });

  test("article counts are grouped by year, most recent first", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Maria Alice Veiga Ferreira De Souza" }).click();

    const years = page.locator("tbody tr td:first-child");
    await expect(years.nth(0)).toHaveText("2025");
    await expect(years.nth(1)).toHaveText("2024");
    await expect(years.nth(2)).toHaveText("2023");
  });

  test("empty sections render as empty states", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Ana Paula Sem Dados" }).click();

    await expect(
      page.getByRole("region", { name: "Articles" }).getByText("No articles recorded."),
    ).toBeVisible();
    await expect(page.getByText("No current projects.")).toBeVisible();
  });

  test("loading state is shown while fetching", async ({ page }) => {
    await page.route("**/api/professors/1**", async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 800));
      await route.continue();
    });
    await page.goto("/professors/1");
    await expect(page.getByRole("status").first()).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  });

  test("unknown professor shows friendly error", async ({ page }) => {
    await page.goto("/professors/99999");
    await expect(page.getByText("Professor not found.")).toBeVisible();
  });
});