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

test("persists a worker completion and links its immutable artifact", async ({ page, request }) => {
  const apiBase = "http://127.0.0.1:8100";
  const workerHeaders = { Authorization: "Bearer rrw_e2e-worker.e2e-only-secret" };
  const capabilities = {
    worker_id: "e2e-worker",
    cuda: true,
    gpu_name: "deterministic-e2e-fixture",
    vram_gb: 80,
    adapters: ["vla_eval_lerobot"],
    environments: ["vla-eval-libero-object"],
  };

  await page.goto("/policies/pi05-libero");
  await page.getByRole("button", { name: "Run LIBERO eval" }).click();
  await expect(page).toHaveURL(/\/evaluations\/eval-/);
  const jobId = page.url().split("/").at(-1)!;

  const registration = await request.post(`${apiBase}/private/workers/register`, {
    headers: workerHeaders,
    data: capabilities,
  });
  expect(registration.ok()).toBeTruthy();
  const claim = await request.post(`${apiBase}/private/workers/claim`, {
    headers: workerHeaders,
    data: capabilities,
  });
  expect(claim.ok()).toBeTruthy();
  expect((await claim.json()).id).toBe(jobId);
  const heartbeat = await request.post(`${apiBase}/private/workers/jobs/${jobId}/heartbeat`, {
    headers: workerHeaders,
  });
  expect(heartbeat.ok()).toBeTruthy();

  const grant = await request.post(`${apiBase}/private/workers/jobs/${jobId}/artifacts/presign`, {
    headers: workerHeaders,
    data: {
      kind: "log",
      filename: "e2e-result.log",
      media_type: "text/plain",
      sha256: "b".repeat(64),
      size_bytes: 18,
    },
  });
  expect(grant.ok()).toBeTruthy();
  const grantedArtifact = (await grant.json()).artifact;
  const fixtureResponse = await request.get(`${apiBase}/v0/rollouts/rollout-upstream-pi05-libero-object`);
  const fixture = await fixtureResponse.json();
  const rolloutId = `rollout-${jobId}`;
  const completion = await request.post(`${apiBase}/private/workers/jobs/${jobId}/complete`, {
    headers: workerHeaders,
    data: {
      rollouts: [{
        ...fixture,
        id: rolloutId,
        evaluation_job_id: jobId,
        metrics: { success_rate: 1 },
        artifacts: [grantedArtifact],
        evidence_note: "Executed by the deterministic browser E2E fixture worker.",
      }],
    },
  });
  expect(completion.ok()).toBeTruthy();

  await page.reload();
  await expect(page.getByRole("heading", { name: "succeeded" })).toBeVisible();
  await page.getByRole("link", { name: rolloutId }).click();
  await expect(page.getByText("Executed by the deterministic browser E2E fixture worker.")).toBeVisible();
  await expect(page.getByText("b".repeat(64))).toBeVisible();
  await expect(page.getByText("log · 18 bytes")).toBeVisible();
});
