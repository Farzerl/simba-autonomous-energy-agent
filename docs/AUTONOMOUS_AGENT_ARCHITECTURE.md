# SIMBA Autonomous Energy Operations Agent architecture

## Boundary

The agent is a persistent mission controller across all configured facilities. It does
not replace electrical calculation, forecasting, protection or operator authority.

```text
Mission goal
  -> compact observation (campus, facilities, Chronos routes, tariff, anomalies)
  -> deterministic candidates from configured flexible loads/devices
  -> Energy Safety Firewall
  -> multi-objective plan ranking
  -> optional local model selects only among valid plan IDs
  -> Approval mission: approve | modify | reject | approve-with-limits
  -> simulation-only control gateway
  -> observed response and deterministic verification
  -> target met, or replan inside approval limits
  -> persistent audit trail
```

## State model

```text
CREATED -> OBSERVING -> RISK_DETECTED -> PLANNING -> PLAN_READY
        -> AWAITING_APPROVAL
             | approve / approve-with-limits -> APPROVED -> EXECUTING
             | modify -> PLANNING
             | reject -> REJECTED
        -> OBSERVING_RESPONSE -> TARGET_MET
                              -> REPLANNING -> PLAN_READY -> APPROVED
                              -> FAILED
```

Terminal missions can be closed. Every transition emits a sequenced JSON event into
the mission record and append-only JSONL audit file.

## Responsibility map

| Component | Authority |
|---|---|
| Existing Chronos-2 demand and power-quality routes | Numerical forecast; unchanged weights |
| Existing tariff engine | Time-of-use period/rate |
| Existing anomaly logic | Findings and escalation context |
| Device emulator and scenario map | Availability, classification, capacity, response |
| Candidate generator | Deterministic non-critical actions only |
| Response estimator | Conservative configured emulator/history factor and confidence |
| Plan optimizer | Coverage, safety, confidence, disruption, cost, compactness |
| Energy Safety Firewall | Final deterministic action/plan permission |
| Approval mission | Operator identity, decision, plan version and limits |
| Control gateway | Simulation transport only for Gate 1 |
| Verifier | Realised response, headroom, target status and replan gap |
| Optional local LLM | Select a valid plan ID and explain/replan semantically |

## Safety firewall

An action is rejected when any of these conditions applies:

- classification is critical or absent from the configured flexible set;
- action is unsupported, over device/load capacity, or breaches the protected floor;
- device is missing, offline, unhealthy, locally controlled or unavailable;
- action expiry is stale;
- operator approval is absent at execution;
- plan exceeds action count, total reduction, facility, load-group or expiry limits;
- any request attempts live electrical control.

The complication demo marks one emulated device unavailable. The first execution
attempt records the firewall block, excludes the failed candidate, replans from the
remaining configured loads, executes inside the approval limits and verifies the goal.
The original device state is restored after the demonstration.

## Provider and memory design

`SIMBA_AGENT_PROVIDER=mock` is the safe default. It makes zero model calls and selects
the top deterministic plan. `SIMBA_AGENT_PROVIDER=llama_server` uses a persistent
localhost-only OpenAI-compatible llama.cpp endpoint. The provider receives compact
JSON, uses a 2,048-token context and a 160-token output ceiling, caches identical
selections, validates the returned plan ID, and falls back to deterministic ranking on
any error. No facility state is sent over the internet.

The official Gate 1 profiler independently launches the submitted GGUF using its own
llama.cpp pipeline. The application provider abstraction does not alter that contract.

## Persistence

- `runtime/agent/missions.json`: atomic mission snapshot store.
- `runtime/agent/events.jsonl`: append-only transition/action evidence.
- Existing actuation runtime: device acknowledgements and emulator evidence.

Runtime state is excluded from Git. Tests and benchmarks use isolated temporary paths.
