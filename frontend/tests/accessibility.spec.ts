import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const SCREENS: { name: string; path: string; setup?: (page: import("@playwright/test").Page) => Promise<void> }[] = [
  { name: "directory", path: "/" },
  { name: "profile", path: "/professors/1" },
  { name: "login", path: "/login" },
  {
    name: "admin",
    path: "/admin",
    setup: async (page) => {
      await page.getByLabel("Username").fill("admin");
      await page.getByLabel("Password").fill("admin123");
      await page.getByRole("button", { name: "Sign in" }).click();
      await expect(page.getByRole("heading", { name: "Admin" })).toBeVisible();
    },
  },
];

for (const screen of SCREENS) {
  test(`accessibility audit: ${screen.name} has no serious violations`, async ({
    page,
  }) => {
    await page.goto(screen.path);
    if (screen.setup) await screen.setup(page);
    const results = await new AxeBuilder({ page }).analyze();
    const serious = results.violations.filter(
      (violation) =>
        violation.impact === "critical" || violation.impact === "serious",
    );
    expect(
      serious.map((violation) => ({
        id: violation.id,
        impact: violation.impact,
        nodes: violation.nodes.length,
      })),
    ).toEqual([]);
  });
}

test("accessibility audit: contrast passes on the directory screen", async ({
  page,
}) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2aa"])
    .analyze();
  const contrast = results.violations.filter(
    (violation) => violation.id === "color-contrast",
  );
  expect(contrast).toEqual([]);
});

test("accessibility audit: 200% zoom keeps directory usable", async ({
  page,
}) => {
  await page.goto("/");
  await page.evaluate(() => {
    document.documentElement.style.fontSize = "32px";
  });
  const results = await new AxeBuilder({ page }).analyze();
  const blocking = results.violations.filter(
    (violation) => violation.id === "scrollable-region-focusable",
  );
  expect(blocking).toEqual([]);
  await expect(
    page.getByRole("heading", { name: "Professor directory" }),
  ).toBeVisible();
});