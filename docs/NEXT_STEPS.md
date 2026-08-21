# RoboRouter next-step execution order

The GitHub remote is active at `git@github.com:richik-p/roborouter.git`. Execute the
remaining work in this order; the order deliberately puts the internet-facing safety
boundary before the expensive GPU run.

1. **Deploy the TLS control plane and provision the NVIDIA worker.** Worker identity,
   bounded rotation, deterministic completed-job E2E, and deployment templates are
   now ready. Follow
   [`operations/REMOTE_EVALUATION_RUNBOOK.md`](operations/REMOTE_EVALUATION_RUNBOOK.md).
2. **Run one π₀.₅/LIBERO Object episode.** Complete and sign off
   [`plans/remote-evaluation.md`](plans/remote-evaluation.md).
3. **Run the matched LIBERO Goal pair.** Use exactly the same environment revision,
   task revision, evaluator, action/observation contracts, and seed list for π₀.₅ and
   MolmoAct2. Do not call the result matched if any identity differs.
4. **Complete the UAV simulation spike.** Follow
   [`plans/uav-px4-sitl-spike.md`](plans/uav-px4-sitl-spike.md). Keep physical
   actuation structurally absent.

The next blockers are external inputs: three DNS names, a public Linux control-plane
host, an NVIDIA Linux machine, and the operator's preferred infrastructure provider.
