import { expect, test } from "@playwright/test";

const email = process.env.STORY_ENGINE_NEXT_QA_EMAIL;
const password = process.env.STORY_ENGINE_NEXT_QA_PASSWORD;

test.beforeEach(async ({ page }) => {
  test.skip(!email || !password, "Synthetic QA credentials are required.");
  await page.goto("/story-engine-next/dashboard");
  await page.getByLabel(/email/i).fill(email!);
  await page.getByLabel(/password/i).fill(password!);
  await page.getByRole("button", { name: /sign in/i }).click();
  await expect(page).toHaveURL(/story-engine-next/);
});

test("draws five random Cards and keeps generation beside the session", async ({
  page,
}) => {
  const sessions = await page.evaluate(() =>
    fetch("/api/story-engine-next/brainstorm/").then((response) =>
      response.json(),
    ),
  );
  await page.goto(`/story-engine-next/brainstorm/${sessions.sessions[0].id}`);
  await page.getByRole("button", { name: "Draw", exact: true }).click();
  await page.getByRole("button", { name: "5 Cards" }).click();
  await expect(page.locator(".card-chip")).toHaveCount(5);
  await page.getByRole("button", { name: /Generate Plot Seeds/ }).click();
  await expect(page.locator(".result-editor")).toBeVisible();
});

test("opens every Character section through stable URLs", async ({ page }) => {
  const payload = await page.evaluate(() =>
    fetch("/api/story-engine-next/characters/").then((response) =>
      response.json(),
    ),
  );
  const id = payload.characters[0].id;
  for (const section of [
    "overview",
    "appearance",
    "personality",
    "backstory",
    "abilities",
    "relationships",
    "arc-notes",
    "progression",
    "evaluation",
    "appearances",
  ]) {
    await page.goto(`/story-engine-next/characters/${id}/${section}`);
    await expect(page).toHaveURL(new RegExp(`${section}$`));
    await expect(page.locator(".character-tabs .active")).toBeVisible();
  }
});
