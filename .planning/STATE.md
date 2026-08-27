# State

**Milestone:** SPADE joint protocol  
**Status:** active  
**Current phase:** Manufacturing certificate recovery — LOO-tail+Vmax gate

## Decisions frozen

- Exactly 48 evaluations per arm per campaign.
- Public method name remains SPADE.
- Existing families are development-only; four new randomized generators form lockbox.
- Primary target is future-response reliability at gamma 0.95.
- Certificate validation is empirical truth containment, not model-internal non-rejection.
- Development compares exactly three policies by three opening sizes.
- Lockbox success is a four-endpoint conjunction required in every family.
- Manufacturing claim hierarchy: qualified CE → round economy → setpoint parity → map vs
  Sobol; Plate-2 targeting is tertiary / historical only.
- Current registered certificate recovery: `smallest` CE + assay predictive noise +
  `loo_calibration_tail` latent inflation + `certificate_max_volume: 0.001`.

## Protocol digests

| study | digest | outcome |
|---|---|---|
| joint v1 | `00ce6971…` | `NO_SELECTION` (archived) |
| mfg assay+smallest | `f6eca072…` | shortfall (hill best emp 0.878); archived |
| mfg LOO-RMS+Vmax | `6e6dec2a…` | hill ok / levy emp ~0.72; archived |
| **mfg LOO-tail+Vmax (current)** | `6f38077e…` | gate then full 5×50 |

## Next action

1. Gate hill+levy keys 0–15 under LOO-tail+Vmax; only continue full 5×50 if a
   candidate clears ans≥0.5 and emp≥0.9 on both.
2. Full REGISTERED 5×50 → LOFO → only if `SELECTED` then power → lockbox.
3. Do not claim SPADE manufacturing-superior until SELECTED + POWERED + lockbox PASS.
4. Do not reopen archived lockbox / v1 / assay / LOO-RMS shortfall as confirmatory.
