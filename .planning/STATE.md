# State

**Milestone:** SPADE joint protocol  
**Status:** active  
**Current phase:** Manufacturing certificate recovery — LOO+Vmax development RUNNING

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
  `loo_calibration` latent inflation + `certificate_max_volume: 0.001`.

## Protocol digests

| study | digest | outcome |
|---|---|---|
| joint v1 | `00ce6971…` | `NO_SELECTION` (archived) |
| mfg assay+smallest | `f6eca072…` | shortfall (hill best emp 0.878); archived |
| **mfg LOO+Vmax (current)** | `6e6dec2a…` | development in flight |

## Next action

1. Complete REGISTERED 5×50 under `6e6dec2a…` via `scripts/spade_development_watchdog.sh`.
2. Auto LOFO → only if `SELECTED` then power → lockbox.
3. Do not reopen archived lockbox / v1 / assay-shortfall as confirmatory.
4. Update RESEARCH-SUMMARY manufacturing claims only after confirmatory PASS.
