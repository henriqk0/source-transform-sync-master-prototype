import { expect, test } from "@playwright/test";

test("login page signs in admin and lands on admin page", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password").fill("admin123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/admin/);
  await expect(page.getByRole("heading", { name: "Admin" })).toBeVisible();
});

test("login page signs in professor and lands on directory", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("maria");
  await page.getByLabel("Password").fill("maria123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(
    page.getByRole("heading", { name: "Professor directory" }),
  ).toBeVisible();
});

test("login page shows error for wrong credentials", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("maria");
  await page.getByLabel("Password").fill("wrong");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Invalid username or password")).toBeVisible();
});

test("admin registers a professor from the admin page", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password").fill("admin123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Admin" })).toBeVisible();

  await page.getByLabel("Full name").fill("Novo Professor");
  await page.getByLabel("Emails (comma-separated)").fill("novo@ifes.edu.br");
  await page.getByLabel("Username").fill("novo");
  await page.getByLabel("Password (min 8 characters)").fill("novo-secret");
  await page.getByRole("button", { name: "Register professor" }).click();
  await expect(page.getByText("Professor registered: novo")).toBeVisible();

  const created = await page.getByText(/researcher id \d+/).textContent();
  const match = created?.match(/researcher id (\d+)/);
  expect(match).not.toBeNull();
});

test("duplicate registration surfaces the 400 message", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password").fill("admin123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByRole("heading", { name: "Admin" })).toBeVisible();

  await page.getByLabel("Full name").fill("Duplicado");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password (min 8 characters)").fill("dup-secret");
  await page.getByRole("button", { name: "Register professor" }).click();
  await expect(page.getByText("Username already exists")).toBeVisible();
});

test("professor edits own data on profile page", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("maria");
  await page.getByLabel("Password").fill("maria123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/$/);

  await page
    .getByRole("link", { name: "Maria Alice Veiga Ferreira De Souza" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Edit your data" }),
  ).toBeVisible();

  await page.getByLabel("Emails (comma-separated)").fill("maria.nova@ifes.edu.br");
  await page.getByRole("button", { name: "Save changes" }).click();
  await expect(page.getByText("Your data was updated.")).toBeVisible();
});

test("professor cannot see edit form on another professor", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Username").fill("maria");
  await page.getByLabel("Password").fill("maria123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/$/);

  await page
    .getByRole("link", { name: "Carlos Roberto Pires Campos" })
    .click();
  await expect(page.getByRole("heading", { name: "Edit your data" })).toHaveCount(
    0,
  );
});