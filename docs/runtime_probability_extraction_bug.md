# Runtime Probability Extraction Bug

## Finding

The live inference runtime was misinterpreting scalar model outputs from the TCN model.

The current TCN classifier returns a single logit, not a final probability.
Training and notebook evaluation convert that logit with `sigmoid(logit)`.

However, the runtime extraction logic in `src/services/model_runtime_service.py` previously did this:

- if the scalar output was between `0` and `1`, treat it as an already-final probability
- otherwise, apply sigmoid

That behavior is incorrect for this model.

Example:

- raw model output: `0.20`
- correct probability: `sigmoid(0.20) ~= 0.5498`
- buggy runtime stored value: `0.20`

This created a strong bearish skew in live system history because many mildly bullish or neutral positive logits were being recorded as low probabilities.

## Impact

This bug can make the live system look much more bearish than the model actually is.

Observed effects during investigation:

- far too many stored live `probability_up` values below the sell threshold
- very few live BUY signals
- short-only execution behavior in historical trades
- mismatch between offline test-set probability distributions and live system probability distributions

## Fix

The runtime extractor now treats scalar outputs as logits by default.

The only scalar outputs treated as already-final probabilities are explicit `probability_up` payloads from dictionary-based model outputs.

This keeps compatibility with future explicit-probability outputs while correctly handling the current TCN model.

## History Preservation

Historical parquet data was intentionally left unchanged.

The fix applies only to future runtime inferences and downstream signal / strategy / risk decisions generated after the patch.
