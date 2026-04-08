# Model Card: Pitch Prediction Models

## Overall Benchmark

All models predict simplified pitch types: **fast**, **breaking**, **off-speed**.

| Model | Overall | Fast | Breaking | Off-Speed | N Pitches |
|-------|---------|------|----------|-----------|-----------|
| Naive (Always Fast) | 0.5643 | 1.0000 | 0.0000 | 0.0000 | 24,917 |
| N-Gram (n=3) | 0.5335 | 0.7795 | 0.2496 | 0.1121 | 24,917 |
| N-Gram (n=4) | 0.5376 | 0.8223 | 0.1977 | 0.0837 | 24,917 |
| Frequency-Based (Oracle) | 0.4822 | 0.6019 | 0.3729 | 0.1915 | 24,917 |
| Markov Context | 0.5552 | 0.9493 | 0.0540 | 0.0175 | 24,917 |
| Transformer | 0.6109 | 0.9285 | 0.2421 | 0.0743 | 24,917 |

## Per-Pitcher Lift Over Naive Baseline

Sorted by fastball rate (low = junk ballers, high = fastball-heavy).
**Lift** = best model accuracy − naive (always-fast) accuracy. Positive = model beats naive.

| Pitcher | Fast% | N | Naive | N-Gram (n=3) | N-Gram (n=4) | Frequency-Based (Oracle) | Markov Context | Transformer | Best Lift |
|---------|-------|---|-------|------------|------------|------------------------|--------------|-----------|----------|
| Valdez, Framber | 40.0% | 1,419 | 0.400 | 0.428 | 0.422 | 0.375 | 0.407 | 0.519 | +0.119 |
| McClanahan, Shane | 40.2% | 645 | 0.402 | 0.369 | 0.394 | 0.357 | 0.394 | 0.329 | -0.008 |
| Darvish, Yu | 40.4% | 961 | 0.404 | 0.475 | 0.438 | 0.486 | 0.414 | 0.663 | +0.259 |
| Sale, Chris | 44.5% | 805 | 0.445 | 0.450 | 0.439 | 0.414 | 0.431 | 0.578 | +0.133 |
| Snell, Blake | 45.6% | 1,147 | 0.456 | 0.448 | 0.464 | 0.371 | 0.445 | 0.554 | +0.098 |
| Gallen, Zac | 47.7% | 1,517 | 0.477 | 0.447 | 0.462 | 0.396 | 0.474 | 0.481 | +0.003 |
| Verlander, Justin | 48.4% | 1,213 | 0.484 | 0.445 | 0.445 | 0.395 | 0.478 | 0.648 | +0.164 |
| Glasnow, Tyler | 49.3% | 615 | 0.493 | 0.532 | 0.520 | 0.525 | 0.509 | 0.696 | +0.203 |
| Scherzer, Max | 51.4% | 755 | 0.514 | 0.468 | 0.483 | 0.397 | 0.501 | 0.514 | +0.000 |
| Webb, Logan | 52.6% | 1,443 | 0.526 | 0.484 | 0.506 | 0.420 | 0.511 | 0.570 | +0.044 |
| Burnes, Corbin | 53.6% | 1,388 | 0.536 | 0.480 | 0.491 | 0.417 | 0.525 | 0.536 | +0.000 |
| Ragans, Cole | 54.2% | 840 | 0.542 | 0.483 | 0.502 | 0.379 | 0.527 | 0.543 | +0.001 |
| Lugo, Seth | 54.6% | 845 | 0.546 | 0.484 | 0.499 | 0.466 | 0.538 | 0.573 | +0.027 |
| Skubal, Tarik | 55.8% | 988 | 0.558 | 0.470 | 0.511 | 0.402 | 0.552 | 0.553 | -0.005 |
| Strider, Spencer | 58.0% | 822 | 0.580 | 0.530 | 0.517 | 0.462 | 0.569 | 0.589 | +0.008 |
| Nola, Aaron | 58.1% | 1,646 | 0.581 | 0.534 | 0.531 | 0.470 | 0.571 | 0.581 | +0.000 |
| Cole, Gerrit | 60.0% | 1,363 | 0.600 | 0.543 | 0.560 | 0.510 | 0.590 | 0.600 | +0.000 |
| Gray, Sonny | 60.2% | 1,213 | 0.602 | 0.560 | 0.566 | 0.458 | 0.599 | 0.628 | +0.026 |
| Houck, Tanner | 60.9% | 699 | 0.609 | 0.564 | 0.538 | 0.531 | 0.607 | 0.614 | +0.004 |
| Ohtani, Shohei | 61.0% | 777 | 0.610 | 0.575 | 0.566 | 0.548 | 0.596 | 0.763 | +0.153 |
| Miller, Bryce | 73.7% | 832 | 0.737 | 0.673 | 0.661 | 0.632 | 0.715 | 0.737 | +0.000 |
| Wheeler, Zack | 75.9% | 1,558 | 0.759 | 0.729 | 0.730 | 0.644 | 0.727 | 0.759 | +0.000 |
| Gausman, Kevin | 92.4% | 1,426 | 0.924 | 0.914 | 0.910 | 0.849 | 0.909 | 0.924 | +0.000 |

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
| fast | 8464 | 4235 | 1362 |
| breaking | 4190 | 3024 | 895 |
| off-speed | 1359 | 862 | 526 |

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
| fast | 13056 | 764 | 241 |
| breaking | 6022 | 1963 | 124 |
| off-speed | 2259 | 284 | 204 |

</details>
