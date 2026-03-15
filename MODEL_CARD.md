# Model Card: Pitch Prediction Models

## Benchmark Results

All models predict simplified pitch types: **fast**, **breaking**, **off-speed**.

| Model | Overall | Fast | Breaking | Off-Speed | N Pitches |
|-------|---------|------|----------|-----------|-----------|
| Naive (Always Fast) | 0.5643 | 1.0000 | 0.0000 | 0.0000 | 24,917 |
| N-Gram (n=3) | 0.5335 | 0.7795 | 0.2496 | 0.1121 | 24,917 |
| N-Gram (n=4) | 0.5376 | 0.8223 | 0.1977 | 0.0837 | 24,917 |
| Frequency-Based (Oracle) | 0.4834 | 0.5979 | 0.3775 | 0.2104 | 24,917 |
| Markov Context | 0.5552 | 0.9493 | 0.0540 | 0.0175 | 24,917 |

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
