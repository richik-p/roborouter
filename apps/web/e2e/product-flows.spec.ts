import { expect, test } from "@playwright/test";

test("discovers π₀.₅ and explains compatibility", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText(/22 POLICIES/)).toBeVisible();
  await page.getByLabel("Policy or capability").fill("π₀.₅");
  await expect(page.getByText("π₀.₅ LIBERO", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Check compatibility" }).click();
  const policyRow = page.getByRole("link", { name: /π₀.₅ LIBERO/ });
  await expect(policyRow.getByText("SIM VERIFIED", { exact: true })).toBeVisible();
});

test("discovers a UAV policy without reusing arm semantics", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Policy or capability").fill("AeroVLA");
  await expect(page.getByText("AeroVLA", { exact: true })).toBeVisible();
  await expect(page.getByText("aerial / multirotor", { exact: true })).toBeVisible();
});

test("shows exact policy source, runtime, and evidence identity", async ({ page }) => {
  await page.goto("/policies/pi05-libero");
  await expect(page.getByText("lerobot-pi05-libero-finetuned", { exact: true })).toBeVisible();
  await expect(page.getByText("lerobot/pi05_libero_finetuned_v044", { exact: true })).toBeVisible();
  await expect(page.getByText("UPSTREAM REPRODUCTION", { exact: true })).toBeVisible();
});

test("opens an evidence-qualified fixture Rollout", async ({ page }) => {
  await page.goto("/rollouts/rollout-upstream-pi05-libero-object");
  await expect(page.getByRole("heading", { name: "Rollout evidence" })).toBeVisible();
  await expect(page.getByText("Successful", { exact: true })).toBeVisible();
  await expect(page.getByText(/not a RoboRouter-executed episode/)).toBeVisible();
  await expect(page.getByText("8e174154ef5f6c60a8da12ae99c303d8963138c1")).toBeVisible();
});

test("renders a completed matched comparison with exact Rollout links", async ({ page }) => {
  await page.goto("/compare");
  await expect(page.getByText("Matched result set")).toBeVisible();
  await expect(page.getByText("98% success")).toBeVisible();
  await expect(page.getByText("97% success")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open exact Rollout" })).toHaveCount(2);
});

test("refuses a matched label when one result identity differs", async ({ page }) => {
  await page.route("**/v0/rollouts?*", async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    const changed = body.items.map((item: { policy_spec_id: string; seed: number }) =>
      item.policy_spec_id === "molmoact2-libero" ? { ...item, seed: item.seed + 1 } : item,
    );
    await route.fulfill({ response, json: { ...body, items: changed } });
  });
  await page.goto("/compare");
  await expect(page.getByText("Non-comparable")).toBeVisible();
  await expect(page.getByText("Matched result set")).toHaveCount(0);
});

test("launches and cancels a queued evaluation", async ({ page }) => {
  await page.goto("/policies/pi05-libero");
  await page.getByRole("button", { name: "Run LIBERO eval" }).click();
  await expect(page).toHaveURL(/\/evaluations\/eval-/);
  await expect(page.getByRole("heading", { name: "queued" })).toBeVisible();
  await page.getByRole("button", { name: "Cancel evaluation" }).click();
  await expect(page.getByRole("heading", { name: "canceled" })).toBeVisible();
  await expect(page.getByText("Evaluation canceled", { exact: true })).toBeVisible();
});
