# Model Card: Pitch Prediction Models

## Overall Benchmark

All models predict simplified pitch types: **fast**, **breaking**, **off-speed**.

| Model | Overall | Fast | Breaking | Off-Speed | N Pitches |
|-------|---------|------|----------|-----------|-----------|
| Naive (Always Fast) | 0.5643 | 1.0000 | 0.0000 | 0.0000 | 24,917 |
| N-Gram (n=3) | 0.5335 | 0.7795 | 0.2496 | 0.1121 | 24,917 |
| N-Gram (n=4) | 0.5376 | 0.8223 | 0.1977 | 0.0837 | 24,917 |
| Frequency-Based (Oracle) | 0.4794 | 0.5984 | 0.3639 | 0.2115 | 24,917 |
| Markov Context | 0.5552 | 0.9493 | 0.0540 | 0.0175 | 24,917 |
| Transformer | 0.5946 | 0.8898 | 0.2618 | 0.0659 | 24,917 |

## Per-Pitcher Lift Over Naive Baseline

Sorted by fastball rate (low = junk ballers, high = fastball-heavy).
**Lift** = best model accuracy − naive (always-fast) accuracy. Positive = model beats naive.

| Pitcher | Fast% | N | Naive | N-Gram (n=3) | N-Gram (n=4) | Frequency-Based (Oracle) | Markov Context | Transformer | Best Lift |
|---------|-------|---|-------|------------|------------|------------------------|--------------|-----------|----------|
| Valdez, Framber | 40.0% | 1,419 | 0.400 | 0.428 | 0.422 | 0.366 | 0.407 | 0.518 | +0.118 |
| McClanahan, Shane | 40.2% | 645 | 0.402 | 0.369 | 0.394 | 0.380 | 0.394 | 0.335 | -0.008 |
| Darvish, Yu | 40.4% | 961 | 0.404 | 0.475 | 0.438 | 0.472 | 0.414 | 0.587 | +0.183 |
| Sale, Chris | 44.5% | 805 | 0.445 | 0.450 | 0.439 | 0.405 | 0.431 | 0.450 | +0.005 |
| Snell, Blake | 45.6% | 1,147 | 0.456 | 0.448 | 0.464 | 0.391 | 0.445 | 0.513 | +0.057 |
| Gallen, Zac | 47.7% | 1,517 | 0.477 | 0.447 | 0.462 | 0.405 | 0.474 | 0.476 | -0.001 |
| Verlander, Justin | 48.4% | 1,213 | 0.484 | 0.445 | 0.445 | 0.403 | 0.478 | 0.586 | +0.102 |
| Glasnow, Tyler | 49.3% | 615 | 0.493 | 0.532 | 0.520 | 0.517 | 0.509 | 0.712 | +0.220 |
| Scherzer, Max | 51.4% | 755 | 0.514 | 0.468 | 0.483 | 0.418 | 0.501 | 0.514 | +0.000 |
| Webb, Logan | 52.6% | 1,443 | 0.526 | 0.484 | 0.506 | 0.423 | 0.511 | 0.534 | +0.008 |
| Burnes, Corbin | 53.6% | 1,388 | 0.536 | 0.480 | 0.491 | 0.445 | 0.525 | 0.537 | +0.001 |
| Ragans, Cole | 54.2% | 840 | 0.542 | 0.483 | 0.502 | 0.408 | 0.527 | 0.545 | +0.004 |
| Lugo, Seth | 54.6% | 845 | 0.546 | 0.484 | 0.499 | 0.451 | 0.538 | 0.544 | -0.001 |
| Skubal, Tarik | 55.8% | 988 | 0.558 | 0.470 | 0.511 | 0.411 | 0.552 | 0.545 | -0.006 |
| Strider, Spencer | 58.0% | 822 | 0.580 | 0.530 | 0.517 | 0.456 | 0.569 | 0.582 | +0.001 |
| Nola, Aaron | 58.1% | 1,646 | 0.581 | 0.534 | 0.531 | 0.450 | 0.571 | 0.583 | +0.002 |
| Cole, Gerrit | 60.0% | 1,363 | 0.600 | 0.543 | 0.560 | 0.486 | 0.590 | 0.600 | +0.000 |
| Gray, Sonny | 60.2% | 1,213 | 0.602 | 0.560 | 0.566 | 0.475 | 0.599 | 0.636 | +0.034 |
| Houck, Tanner | 60.9% | 699 | 0.609 | 0.564 | 0.538 | 0.545 | 0.607 | 0.620 | +0.010 |
| Ohtani, Shohei | 61.0% | 777 | 0.610 | 0.575 | 0.566 | 0.561 | 0.596 | 0.701 | +0.091 |
| Miller, Bryce | 73.7% | 832 | 0.737 | 0.673 | 0.661 | 0.624 | 0.715 | 0.737 | +0.000 |
| Wheeler, Zack | 75.9% | 1,558 | 0.759 | 0.729 | 0.730 | 0.637 | 0.727 | 0.759 | +0.000 |
| Gausman, Kevin | 92.4% | 1,426 | 0.924 | 0.914 | 0.910 | 0.863 | 0.909 | 0.924 | +0.000 |

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
| fast | 8414 | 4282 | 1365 |
| breaking | 4310 | 2951 | 848 |
| off-speed | 1352 | 814 | 581 |

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
| fast | 12511 | 1293 | 257 |
| breaking | 5890 | 2123 | 96 |
| off-speed | 2359 | 207 | 181 |

</details>
