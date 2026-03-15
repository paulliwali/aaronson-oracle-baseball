# Model Card: Pitch Prediction Models

## Benchmark Results

All models predict simplified pitch types: **fast**, **breaking**, **off-speed**.

| Model | Overall | Fast | Breaking | Off-Speed | N Pitches |
|-------|---------|------|----------|-----------|-----------|
| **PitchGPT Transformer** | **0.6161** | 0.9653 | 0.1897 | 0.0634 | 24,917 |
| Naive (Always Fast) | 0.5643 | 1.0000 | 0.0000 | 0.0000 | 24,917 |
| Markov Context | 0.5552 | 0.9493 | 0.0540 | 0.0175 | 24,917 |
| N-Gram (n=4) | 0.5376 | 0.8223 | 0.1977 | 0.0837 | 24,917 |
| N-Gram (n=3) | 0.5335 | 0.7795 | 0.2496 | 0.1121 | 24,917 |
| Frequency-Based (Oracle) | 0.4834 | 0.5979 | 0.3775 | 0.2104 | 24,917 |

## PitchGPT Transformer

Best model from the `autoresearch/mar14` experiment run (56 experiments).

**Architecture**: 6-layer causal transformer with 4 attention heads, d_model=128, FFN=6x (768), pre-norm, dropout=0.15. Context embeddings for balls/strikes/outs/inning (each d/4=32 dims, concatenated and projected). Learned positional embeddings. ~800K parameters.

**Training**: AdamW (lr=3e-4, weight_decay=0.001), CosineAnnealingLR, batch_size=32, grad_clip=1.0. Fixed 5-minute wall-clock budget on MPS (Apple Silicon). Best checkpoint selected by validation loss.

**Key findings from 56 experiments**:
- Scaling from 4L/64d to 6L/128d gave the biggest single improvement (+2%)
- Dropout 0.15 > 0.12 > 0.10 — regularization matters with small data
- FFN 6x > 4x > 5x > 8x — wider feedforward helps up to a point
- Weight decay 0.001 > 0.01 > 0.0001 — sweet spot for this model size
- High run-to-run variance (0.565–0.616 on identical config) due to random initialization
- Tree models (GBT, Random Forest) fail badly (~0.46–0.57) — sequential structure is critical
- All class-rebalancing attempts hurt accuracy (class weights, focal loss, label smoothing, count priors)
- Weight averaging (SWA, EMA) and ensemble methods did not reliably improve over single best checkpoint
- Model primarily predicts "fast" (~96% of fast pitches correct) with limited minority class accuracy

<details><summary>Confusion: Naive (Always Fast)</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 14061 | 0 | 0 |
| breaking | 8109 | 0 | 0 |
| off-speed | 2747 | 0 | 0 |

</details>

<details><summary>Confusion: N-Gram (n=3)</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 10961 | 2535 | 565 |
| breaking | 5703 | 2024 | 382 |
| off-speed | 1858 | 581 | 308 |

</details>

<details><summary>Confusion: N-Gram (n=4)</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 11563 | 2048 | 450 |
| breaking | 6222 | 1603 | 284 |
| off-speed | 2095 | 422 | 230 |

</details>

<details><summary>Confusion: Frequency-Based (Oracle)</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 8407 | 4332 | 1322 |
| breaking | 4246 | 3061 | 802 |
| off-speed | 1292 | 877 | 578 |

</details>

<details><summary>Confusion: Markov Context</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 13348 | 589 | 124 |
| breaking | 7613 | 438 | 58 |
| off-speed | 2629 | 70 | 48 |

</details>
