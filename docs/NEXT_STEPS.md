# RoboRouter next-step execution order

The GitHub remote is active at `git@github.com:richik-p/roborouter.git`. Execute the
remaining work in this order; the order deliberately puts the internet-facing safety
boundary before the expensive GPU run.

1. **Finish the worker-identity and browser-E2E follow-ups.** The first scoped-token
   implementation, isolation tests, and core browser journeys now exist. Follow the
   remaining items in [`plans/security-and-browser-e2e.md`](plans/security-and-browser-e2e.md),
   especially expiry/rotation and a completed live-worker browser journey.
2. **Deploy the TLS control plane and provision the NVIDIA worker.** Follow
   [`operations/REMOTE_EVALUATION_RUNBOOK.md`](operations/REMOTE_EVALUATION_RUNBOOK.md).
3. **Run one π₀.₅/LIBERO Object episode.** Complete and sign off
   [`plans/remote-evaluation.md`](plans/remote-evaluation.md).
4. **Run the matched LIBERO Goal pair.** Use exactly the same environment revision,
   task revision, evaluator, action/observation contracts, and seed list for π₀.₅ and
   MolmoAct2. Do not call the result matched if any identity differs.
5. **Complete the UAV simulation spike.** Follow
   [`plans/uav-px4-sitl-spike.md`](plans/uav-px4-sitl-spike.md). Keep physical
   actuation structurally absent.

The first external dependency is a Linux NVIDIA machine. The first product-code task
is per-worker credentials; the current single deployment token is acceptable only
for the restricted one-worker smoke topology described in the operations runbook.
