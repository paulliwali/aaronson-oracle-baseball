# Model Card: Pitch Prediction Models

## Overall Benchmark

All models predict simplified pitch types: **fast**, **breaking**, **off-speed**.

| Model | Overall | Fast | Breaking | Off-Speed | N Pitches |
|-------|---------|------|----------|-----------|-----------|
| Naive (Always Fast) | 0.5643 | 1.0000 | 0.0000 | 0.0000 | 24,917 |
| N-Gram (n=3) | 0.5335 | 0.7795 | 0.2496 | 0.1121 | 24,917 |
| N-Gram (n=4) | 0.5376 | 0.8223 | 0.1977 | 0.0837 | 24,917 |
| Frequency-Based (Oracle) | 0.4762 | 0.5967 | 0.3607 | 0.2002 | 24,917 |
| Markov Context | 0.5552 | 0.9493 | 0.0540 | 0.0175 | 24,917 |
| Transformer | 0.5996 | 0.9595 | 0.1632 | 0.0455 | 24,917 |

## Per-Pitcher Lift Over Naive Baseline

Sorted by fastball rate (low = junk ballers, high = fastball-heavy).
**Lift** = best model accuracy − naive (always-fast) accuracy. Positive = model beats naive.

| Pitcher | Fast% | N | Naive | N-Gram (n=3) | N-Gram (n=4) | Frequency-Based (Oracle) | Markov Context | Transformer | Best Lift |
|---------|-------|---|-------|------------|------------|------------------------|--------------|-----------|----------|
| Valdez, Framber | 40.0% | 1,419 | 0.400 | 0.428 | 0.422 | 0.369 | 0.407 | 0.505 | +0.106 |
| McClanahan, Shane | 40.2% | 645 | 0.402 | 0.369 | 0.394 | 0.344 | 0.394 | 0.450 | +0.048 |
| Darvish, Yu | 40.4% | 961 | 0.404 | 0.475 | 0.438 | 0.446 | 0.414 | 0.572 | +0.169 |
| Sale, Chris | 44.5% | 805 | 0.445 | 0.450 | 0.439 | 0.412 | 0.431 | 0.522 | +0.077 |
| Snell, Blake | 45.6% | 1,147 | 0.456 | 0.448 | 0.464 | 0.390 | 0.445 | 0.497 | +0.041 |
| Gallen, Zac | 47.7% | 1,517 | 0.477 | 0.447 | 0.462 | 0.395 | 0.474 | 0.513 | +0.036 |
| Verlander, Justin | 48.4% | 1,213 | 0.484 | 0.445 | 0.445 | 0.438 | 0.478 | 0.529 | +0.045 |
| Glasnow, Tyler | 49.3% | 615 | 0.493 | 0.532 | 0.520 | 0.511 | 0.509 | 0.607 | +0.114 |
| Scherzer, Max | 51.4% | 755 | 0.514 | 0.468 | 0.483 | 0.421 | 0.501 | 0.530 | +0.016 |
| Webb, Logan | 52.6% | 1,443 | 0.526 | 0.484 | 0.506 | 0.413 | 0.511 | 0.560 | +0.034 |
| Burnes, Corbin | 53.6% | 1,388 | 0.536 | 0.480 | 0.491 | 0.434 | 0.525 | 0.553 | +0.017 |
| Ragans, Cole | 54.2% | 840 | 0.542 | 0.483 | 0.502 | 0.395 | 0.527 | 0.545 | +0.004 |
| Lugo, Seth | 54.6% | 845 | 0.546 | 0.484 | 0.499 | 0.415 | 0.538 | 0.572 | +0.026 |
| Skubal, Tarik | 55.8% | 988 | 0.558 | 0.470 | 0.511 | 0.429 | 0.552 | 0.563 | +0.005 |
| Strider, Spencer | 58.0% | 822 | 0.580 | 0.530 | 0.517 | 0.464 | 0.569 | 0.599 | +0.018 |
| Nola, Aaron | 58.1% | 1,646 | 0.581 | 0.534 | 0.531 | 0.470 | 0.571 | 0.591 | +0.010 |
| Cole, Gerrit | 60.0% | 1,363 | 0.600 | 0.543 | 0.560 | 0.515 | 0.590 | 0.619 | +0.018 |
| Gray, Sonny | 60.2% | 1,213 | 0.602 | 0.560 | 0.566 | 0.486 | 0.599 | 0.607 | +0.005 |
| Houck, Tanner | 60.9% | 699 | 0.609 | 0.564 | 0.538 | 0.538 | 0.607 | 0.641 | +0.031 |
| Ohtani, Shohei | 61.0% | 777 | 0.610 | 0.575 | 0.566 | 0.537 | 0.596 | 0.664 | +0.054 |
| Miller, Bryce | 73.7% | 832 | 0.737 | 0.673 | 0.661 | 0.620 | 0.715 | 0.744 | +0.007 |
| Wheeler, Zack | 75.9% | 1,558 | 0.759 | 0.729 | 0.730 | 0.646 | 0.727 | 0.759 | +0.000 |
| Gausman, Kevin | 92.4% | 1,426 | 0.924 | 0.914 | 0.910 | 0.871 | 0.909 | 0.924 | +0.000 |

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
| fast | 8390 | 4266 | 1405 |
| breaking | 4356 | 2925 | 828 |
| off-speed | 1354 | 843 | 550 |

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
| fast | 13492 | 525 | 44 |
| breaking | 6731 | 1323 | 55 |
| off-speed | 2424 | 198 | 125 |

</details>
