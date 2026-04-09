# Model Card: Pitch Prediction Models

## Overall Benchmark

All models predict simplified pitch types: **fast**, **breaking**, **off-speed**.

| Model | Overall | Fast | Breaking | Off-Speed | N Pitches |
|-------|---------|------|----------|-----------|-----------|
| Naive (Always Fast) | 0.5643 | 1.0000 | 0.0000 | 0.0000 | 24,917 |
| N-Gram (n=3) | 0.5335 | 0.7795 | 0.2496 | 0.1121 | 24,917 |
| N-Gram (n=4) | 0.5376 | 0.8223 | 0.1977 | 0.0837 | 24,917 |
| Frequency-Based (Oracle) | 0.4828 | 0.6053 | 0.3665 | 0.1995 | 24,917 |
| Markov Context | 0.5552 | 0.9493 | 0.0540 | 0.0175 | 24,917 |
| Transformer | 0.5976 | 0.9755 | 0.1121 | 0.0968 | 24,917 |

## Per-Pitcher Lift Over Naive Baseline

Sorted by fastball rate (low = junk ballers, high = fastball-heavy).
**Lift** = best model accuracy − naive (always-fast) accuracy. Positive = model beats naive.

| Pitcher | Fast% | N | Naive | N-Gram (n=3) | N-Gram (n=4) | Frequency-Based (Oracle) | Markov Context | Transformer | Best Lift |
|---------|-------|---|-------|------------|------------|------------------------|--------------|-----------|----------|
| Valdez, Framber | 40.0% | 1,419 | 0.400 | 0.428 | 0.422 | 0.383 | 0.407 | 0.462 | +0.062 |
| McClanahan, Shane | 40.2% | 645 | 0.402 | 0.369 | 0.394 | 0.370 | 0.394 | 0.408 | +0.006 |
| Darvish, Yu | 40.4% | 961 | 0.404 | 0.475 | 0.438 | 0.431 | 0.414 | 0.630 | +0.226 |
| Sale, Chris | 44.5% | 805 | 0.445 | 0.450 | 0.439 | 0.416 | 0.431 | 0.474 | +0.030 |
| Snell, Blake | 45.6% | 1,147 | 0.456 | 0.448 | 0.464 | 0.377 | 0.445 | 0.478 | +0.022 |
| Gallen, Zac | 47.7% | 1,517 | 0.477 | 0.447 | 0.462 | 0.398 | 0.474 | 0.477 | +0.000 |
| Verlander, Justin | 48.4% | 1,213 | 0.484 | 0.445 | 0.445 | 0.427 | 0.478 | 0.594 | +0.111 |
| Glasnow, Tyler | 49.3% | 615 | 0.493 | 0.532 | 0.520 | 0.506 | 0.509 | 0.750 | +0.257 |
| Scherzer, Max | 51.4% | 755 | 0.514 | 0.468 | 0.483 | 0.400 | 0.501 | 0.514 | +0.000 |
| Webb, Logan | 52.6% | 1,443 | 0.526 | 0.484 | 0.506 | 0.398 | 0.511 | 0.584 | +0.057 |
| Burnes, Corbin | 53.6% | 1,388 | 0.536 | 0.480 | 0.491 | 0.428 | 0.525 | 0.536 | +0.000 |
| Ragans, Cole | 54.2% | 840 | 0.542 | 0.483 | 0.502 | 0.400 | 0.527 | 0.542 | +0.000 |
| Lugo, Seth | 54.6% | 845 | 0.546 | 0.484 | 0.499 | 0.435 | 0.538 | 0.553 | +0.007 |
| Skubal, Tarik | 55.8% | 988 | 0.558 | 0.470 | 0.511 | 0.428 | 0.552 | 0.560 | +0.002 |
| Strider, Spencer | 58.0% | 822 | 0.580 | 0.530 | 0.517 | 0.471 | 0.569 | 0.582 | +0.001 |
| Nola, Aaron | 58.1% | 1,646 | 0.581 | 0.534 | 0.531 | 0.485 | 0.571 | 0.581 | +0.001 |
| Cole, Gerrit | 60.0% | 1,363 | 0.600 | 0.543 | 0.560 | 0.505 | 0.590 | 0.600 | +0.000 |
| Gray, Sonny | 60.2% | 1,213 | 0.602 | 0.560 | 0.566 | 0.484 | 0.599 | 0.612 | +0.010 |
| Houck, Tanner | 60.9% | 699 | 0.609 | 0.564 | 0.538 | 0.515 | 0.607 | 0.611 | +0.001 |
| Ohtani, Shohei | 61.0% | 777 | 0.610 | 0.575 | 0.566 | 0.511 | 0.596 | 0.705 | +0.095 |
| Miller, Bryce | 73.7% | 832 | 0.737 | 0.673 | 0.661 | 0.617 | 0.715 | 0.737 | +0.000 |
| Wheeler, Zack | 75.9% | 1,558 | 0.759 | 0.729 | 0.730 | 0.641 | 0.727 | 0.759 | +0.000 |
| Gausman, Kevin | 92.4% | 1,426 | 0.924 | 0.914 | 0.910 | 0.858 | 0.909 | 0.924 | +0.000 |

## Confusion Matrices

<details><summary>Naive (Always Fast)</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 14061 | 0 | 0 |
| breaking | 8109 | 0 | 0 |
| off-speed | 2747 | 0 | 0 |

</details>

<details><summary>N-Gram (n=3)</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 10961 | 2535 | 565 |
| breaking | 5703 | 2024 | 382 |
| off-speed | 1858 | 581 | 308 |

</details>

<details><summary>N-Gram (n=4)</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 11563 | 2048 | 450 |
| breaking | 6222 | 1603 | 284 |
| off-speed | 2095 | 422 | 230 |

</details>

<details><summary>Frequency-Based (Oracle)</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 8511 | 4244 | 1306 |
| breaking | 4251 | 2972 | 886 |
| off-speed | 1350 | 849 | 548 |

</details>

<details><summary>Markov Context</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 13348 | 589 | 124 |
| breaking | 7613 | 438 | 58 |
| off-speed | 2629 | 70 | 48 |

</details>

<details><summary>Transformer</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 13716 | 137 | 208 |
| breaking | 7073 | 909 | 127 |
| off-speed | 2431 | 50 | 266 |

</details>
