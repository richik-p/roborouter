# Launch model landscape

**Reconstructed:** 2026-08-20 from official repositories and model cards. This
is an implementation shortlist, not a claim of universal robot compatibility.

## First executable path

- π₀.₅ through LeRobot and `vla-eval` v0.4.0.
- Checkpoint: `lerobot/pi05_libero_finetuned`.
- Initial benchmark: LIBERO Object.
- Evidence: upstream harness reproduction; RoboRouter must retain the exact
  harness, LeRobot, checkpoint, benchmark, container, and seed revisions.

## Second comparable family

- MolmoAct2 checkpoint `allenai/MolmoAct2-LIBERO`.
- Compare with π₀.₅ on the same LIBERO Goal protocol.

## Catalog candidates

Include executable or research-only entries for OpenVLA, OpenVLA-OFT, GR00T
N1.7, X-VLA, SmolVLA, ACT, Diffusion Policy, CogACT/DB-CogACT, Octo, RT-1/RT-2,
RDT, RoboMamba, TinyVLA, LingBot-VA, VLA-JEPA, FastWAM, AeroVLA, and representative
mobile, dexterous-hand, legged, and UAV policies. Evidence and availability must
be checked per entry; a family name alone never implies an executable path.

## Evaluation-layer update

The AllenAI VLA evaluation harness provides the most direct initial boundary
for reproducible hosted evaluation. XPolicyLab remains an adapter/runtime
source. RoboDojo is deferred from the first slice because its Isaac-based path
has larger asset and license requirements.

