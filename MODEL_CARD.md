# Model Card: Pitch Prediction Models

## Ceiling & Experiment Log

The PitchGPT transformer sits at **0.5968** test accuracy on the 103K-pitch test set (naive "always fast" baseline 0.5857, lift +0.0111). Multiple improvement axes were explored and all either failed to beat baseline or collapsed accuracy. The ceiling is accepted as architectural for now.

| Axis | Best variant | Test Acc | vs baseline | Notes |
|------|-------------|----------|-------------|-------|
| Baseline (argmax CE) | 6L / 4H / 128d | **0.5968** | — | Reference |
| Data scaling (apr12) | 675K pitches (4x) | 0.5968 | +0.0000 | Same val loss, more data did not help |
| Post-hoc temp tuning (apr14) | temp=0.5 + thr=0.45 | 0.5987 | +0.0019 | Within noise; all flatten-temp variants worse |
| Post-hoc thresholding (apr14) | any threshold | 0.39–0.59 | −0.00 to −0.20 | Trades acc_fast for acc_brk at net loss |
| Focal loss retrain (apr14) | γ=2.0 | 0.5963 | −0.0005 | Acc_off 0.024→0.053, no net gain |
| Weighted CE retrain (apr14) | inverse-freq | 0.4409 | −0.1559 | Over-correction; output collapses to uniform |

### Things left to try (if revisiting)

- **Two-stage classifier**: fast-vs-not → breaking-vs-offspeed. Decouples the easy decision from the hard 3-way subset.
- **Lighter reweighting**: sqrt-inverse CE or focal γ=3 with alpha weights.
- **Pitch sequence augmentation**: mixup / SpecAugment-style masking during training.
- **Richer context features**: pitch location history, batter handedness interactions, score differential.
- **Ensemble**: PitchGPT × N-Gram × Markov. The models make different errors; voting may lift.

## Overall Benchmark

All models predict simplified pitch types: **fast**, **breaking**, **off-speed**.

| Model | Overall | Fast | Breaking | Off-Speed | N Pitches |
|-------|---------|------|----------|-----------|-----------|
| Naive (Always Fast) | 0.5857 | 1.0000 | 0.0000 | 0.0000 | 103,039 |
| N-Gram (n=3) | 0.5426 | 0.7842 | 0.2344 | 0.1078 | 103,039 |
| Markov Context | 0.5752 | 0.9510 | 0.0524 | 0.0199 | 103,039 |
| Transformer | 0.5968 | 0.9577 | 0.1091 | 0.0237 | 103,039 |

### Retired Models

Dropped from the registry on 2026-04-14 — kept here for the historical record. Both underperformed naive baseline (0.5857) and offered no unique signal worth the surface area.

| Model | Overall | Fast | Breaking | Off-Speed | Reason retired |
|-------|---------|------|----------|-----------|----------------|
| N-Gram (n=4) | 0.5484 | 0.8198 | 0.1927 | 0.0860 | Barely differs from n=3; longer context doesn't help at 3-class granularity |
| Frequency-Based (Oracle) | 0.4912 | 0.6146 | 0.3535 | 0.2139 | Samples rather than predicts — lowest accuracy of any model |

## Per-Pitcher Lift Over Naive Baseline

Sorted by fastball rate (low = junk ballers, high = fastball-heavy).
**Lift** = best model accuracy − naive (always-fast) accuracy. Positive = model beats naive.

| Pitcher | Fast% | N | Naive | N-Gram (n=3) | N-Gram (n=4) | Frequency-Based (Oracle) | Markov Context | Transformer | Best Lift |
|---------|-------|---|-------|------------|------------|------------------------|--------------|-----------|----------|
| Kikuchi, Yusei | 34.6% | 1,766 | 0.346 | 0.433 | 0.419 | 0.433 | 0.367 | 0.501 | +0.155 |
| Blanco, Ronel | 36.3% | 639 | 0.363 | 0.438 | 0.410 | 0.407 | 0.360 | 0.546 | +0.183 |
| Canning, Griffin | 40.2% | 991 | 0.402 | 0.412 | 0.403 | 0.369 | 0.395 | 0.425 | +0.023 |
| McClanahan, Shane | 40.2% | 645 | 0.402 | 0.369 | 0.394 | 0.355 | 0.394 | 0.327 | -0.008 |
| Darvish, Yu | 40.4% | 961 | 0.404 | 0.475 | 0.438 | 0.448 | 0.414 | 0.516 | +0.112 |
| Gomber, Austin | 42.8% | 1,079 | 0.428 | 0.394 | 0.400 | 0.373 | 0.424 | 0.457 | +0.029 |
| Waldron, Matt | 43.8% | 555 | 0.438 | 0.458 | 0.485 | 0.432 | 0.461 | 0.513 | +0.076 |
| Valdez, Framber | 44.1% | 1,871 | 0.442 | 0.410 | 0.437 | 0.380 | 0.437 | 0.504 | +0.063 |
| Sánchez, Cristopher | 44.5% | 1,258 | 0.445 | 0.414 | 0.444 | 0.390 | 0.448 | 0.481 | +0.036 |
| Snell, Blake | 45.6% | 1,147 | 0.456 | 0.448 | 0.464 | 0.400 | 0.445 | 0.501 | +0.045 |
| Sale, Chris | 46.3% | 1,064 | 0.463 | 0.463 | 0.458 | 0.454 | 0.476 | 0.475 | +0.013 |
| Stone, Gavin | 46.5% | 424 | 0.465 | 0.363 | 0.403 | 0.368 | 0.460 | 0.465 | +0.000 |
| López, Pablo | 47.2% | 1,634 | 0.472 | 0.409 | 0.423 | 0.377 | 0.475 | 0.478 | +0.006 |
| Webb, Logan | 47.3% | 1,931 | 0.473 | 0.418 | 0.426 | 0.359 | 0.464 | 0.511 | +0.037 |
| Gallen, Zac | 47.7% | 1,517 | 0.477 | 0.447 | 0.462 | 0.413 | 0.474 | 0.477 | +0.000 |
| Verlander, Justin | 48.4% | 1,213 | 0.484 | 0.445 | 0.445 | 0.418 | 0.478 | 0.586 | +0.102 |
| Glasnow, Tyler | 49.3% | 615 | 0.493 | 0.532 | 0.520 | 0.465 | 0.509 | 0.639 | +0.146 |
| Peralta, Freddy | 49.8% | 1,636 | 0.498 | 0.421 | 0.452 | 0.385 | 0.491 | 0.498 | +0.000 |
| Morton, Charlie | 50.1% | 1,618 | 0.501 | 0.441 | 0.469 | 0.434 | 0.491 | 0.503 | +0.002 |
| Cease, Dylan | 50.2% | 1,913 | 0.502 | 0.496 | 0.499 | 0.486 | 0.502 | 0.503 | +0.001 |
| Lorenzen, Michael | 51.4% | 1,217 | 0.514 | 0.468 | 0.468 | 0.401 | 0.495 | 0.514 | +0.000 |
| Scherzer, Max | 51.4% | 755 | 0.514 | 0.468 | 0.483 | 0.432 | 0.501 | 0.514 | +0.000 |
| Gray, Sonny | 51.5% | 1,537 | 0.515 | 0.501 | 0.484 | 0.419 | 0.533 | 0.532 | +0.019 |
| Sears, JP | 51.5% | 1,406 | 0.515 | 0.436 | 0.460 | 0.423 | 0.513 | 0.520 | +0.005 |
| Peterson, David | 51.5% | 1,255 | 0.515 | 0.461 | 0.466 | 0.414 | 0.508 | 0.515 | +0.000 |
| Lugo, Seth | 52.0% | 1,136 | 0.520 | 0.491 | 0.489 | 0.433 | 0.518 | 0.533 | +0.012 |
| Ragans, Cole | 52.3% | 899 | 0.523 | 0.480 | 0.493 | 0.407 | 0.515 | 0.523 | +0.000 |
| Spence, Mitch | 52.3% | 394 | 0.523 | 0.444 | 0.495 | 0.465 | 0.528 | 0.490 | +0.005 |
| Gore, MacKenzie | 52.8% | 1,454 | 0.527 | 0.469 | 0.475 | 0.402 | 0.508 | 0.527 | +0.000 |
| Herz, DJ | 53.4% | 251 | 0.534 | 0.510 | 0.470 | 0.422 | 0.526 | 0.534 | +0.000 |
| Skubal, Tarik | 53.5% | 1,640 | 0.535 | 0.481 | 0.498 | 0.427 | 0.530 | 0.536 | +0.001 |
| Rodón, Carlos | 54.5% | 1,739 | 0.545 | 0.500 | 0.508 | 0.416 | 0.535 | 0.545 | +0.000 |
| Nola, Aaron | 55.0% | 1,847 | 0.550 | 0.485 | 0.512 | 0.431 | 0.539 | 0.550 | +0.000 |
| Fried, Max | 55.0% | 1,677 | 0.550 | 0.483 | 0.518 | 0.435 | 0.549 | 0.552 | +0.002 |
| Keller, Mitch | 55.0% | 1,668 | 0.550 | 0.501 | 0.511 | 0.473 | 0.540 | 0.557 | +0.007 |
| Quintana, Jose | 55.2% | 1,453 | 0.552 | 0.463 | 0.476 | 0.402 | 0.537 | 0.552 | +0.000 |
| King, Michael | 55.2% | 791 | 0.552 | 0.504 | 0.512 | 0.408 | 0.542 | 0.552 | +0.000 |
| Corbin, Patrick | 56.0% | 1,612 | 0.560 | 0.484 | 0.520 | 0.438 | 0.554 | 0.560 | +0.000 |
| Gilbert, Logan | 57.8% | 1,643 | 0.578 | 0.539 | 0.538 | 0.519 | 0.577 | 0.579 | +0.001 |
| Strider, Spencer | 58.0% | 822 | 0.580 | 0.530 | 0.517 | 0.465 | 0.569 | 0.580 | +0.000 |
| Singer, Brady | 58.1% | 1,650 | 0.581 | 0.511 | 0.524 | 0.528 | 0.576 | 0.586 | +0.005 |
| Berríos, José | 58.2% | 1,671 | 0.582 | 0.515 | 0.520 | 0.461 | 0.564 | 0.582 | +0.000 |
| Pfaadt, Brandon | 58.6% | 1,250 | 0.586 | 0.519 | 0.534 | 0.470 | 0.561 | 0.586 | +0.001 |
| Heaney, Andrew | 58.7% | 1,243 | 0.587 | 0.515 | 0.532 | 0.420 | 0.571 | 0.587 | +0.000 |
| Kirby, George | 58.9% | 1,629 | 0.589 | 0.543 | 0.542 | 0.511 | 0.568 | 0.589 | +0.000 |
| Estes, Joey | 59.0% | 390 | 0.590 | 0.518 | 0.518 | 0.500 | 0.582 | 0.590 | +0.000 |
| Manaea, Sean | 59.4% | 1,233 | 0.594 | 0.550 | 0.544 | 0.463 | 0.586 | 0.594 | +0.000 |
| Ortiz, Luis | 59.4% | 859 | 0.594 | 0.532 | 0.532 | 0.446 | 0.577 | 0.594 | +0.000 |
| Skenes, Paul | 59.6% | 817 | 0.596 | 0.529 | 0.543 | 0.428 | 0.579 | 0.596 | +0.000 |
| Pivetta, Nick | 59.7% | 1,708 | 0.597 | 0.550 | 0.560 | 0.528 | 0.587 | 0.600 | +0.003 |
| Gibson, Kyle | 59.7% | 1,436 | 0.597 | 0.549 | 0.548 | 0.480 | 0.593 | 0.597 | +0.000 |
| Cole, Gerrit | 60.0% | 1,363 | 0.600 | 0.543 | 0.560 | 0.509 | 0.590 | 0.600 | +0.000 |
| Taillon, Jameson | 60.2% | 1,403 | 0.602 | 0.556 | 0.559 | 0.451 | 0.592 | 0.602 | +0.000 |
| Brown, Hunter | 60.5% | 1,440 | 0.605 | 0.535 | 0.555 | 0.473 | 0.593 | 0.605 | +0.000 |
| Ohtani, Shohei | 61.0% | 777 | 0.610 | 0.575 | 0.566 | 0.548 | 0.596 | 0.642 | +0.032 |
| Parker, Mitchell | 62.0% | 839 | 0.620 | 0.560 | 0.549 | 0.528 | 0.614 | 0.620 | +0.000 |
| Anderson, Tyler | 62.2% | 1,604 | 0.622 | 0.562 | 0.572 | 0.521 | 0.604 | 0.622 | +0.000 |
| Irvin, Jake | 62.5% | 1,177 | 0.625 | 0.568 | 0.574 | 0.517 | 0.603 | 0.625 | +0.000 |
| Burnes, Corbin | 62.7% | 1,507 | 0.627 | 0.573 | 0.584 | 0.489 | 0.611 | 0.627 | +0.000 |
| Fedde, Erick | 62.8% | 1,078 | 0.628 | 0.581 | 0.586 | 0.488 | 0.609 | 0.628 | +0.000 |
| Steele, Justin | 63.2% | 1,047 | 0.632 | 0.599 | 0.598 | 0.521 | 0.612 | 0.633 | +0.001 |
| Greene, Hunter | 64.2% | 1,303 | 0.642 | 0.559 | 0.557 | 0.550 | 0.630 | 0.642 | +0.000 |
| Suárez, Albert | 64.5% | 293 | 0.645 | 0.577 | 0.594 | 0.481 | 0.621 | 0.645 | +0.000 |
| Houck, Tanner | 64.6% | 809 | 0.646 | 0.582 | 0.596 | 0.556 | 0.628 | 0.646 | +0.000 |
| Severino, Luis | 64.7% | 1,473 | 0.647 | 0.593 | 0.587 | 0.521 | 0.630 | 0.647 | +0.000 |
| Woods Richardson, Simeon | 65.9% | 672 | 0.659 | 0.621 | 0.604 | 0.558 | 0.643 | 0.631 | -0.016 |
| Lively, Ben | 66.0% | 674 | 0.660 | 0.611 | 0.596 | 0.527 | 0.639 | 0.660 | +0.000 |
| Stroman, Marcus | 67.9% | 1,099 | 0.679 | 0.643 | 0.634 | 0.570 | 0.661 | 0.679 | +0.000 |
| Castillo, Luis | 69.0% | 1,735 | 0.690 | 0.632 | 0.646 | 0.528 | 0.677 | 0.690 | +0.000 |
| Bello, Brayan | 69.3% | 1,409 | 0.693 | 0.645 | 0.642 | 0.541 | 0.671 | 0.693 | +0.000 |
| Bassitt, Chris | 69.7% | 1,862 | 0.697 | 0.647 | 0.654 | 0.569 | 0.673 | 0.697 | +0.000 |
| Nelson, Ryne | 70.1% | 1,212 | 0.701 | 0.658 | 0.651 | 0.583 | 0.677 | 0.701 | +0.000 |
| Cortes, Nestor | 71.4% | 1,081 | 0.714 | 0.668 | 0.669 | 0.556 | 0.699 | 0.714 | +0.000 |
| Rea, Colin | 71.8% | 1,059 | 0.718 | 0.667 | 0.663 | 0.618 | 0.696 | 0.718 | +0.000 |
| Civale, Aaron | 72.3% | 1,231 | 0.723 | 0.677 | 0.661 | 0.617 | 0.705 | 0.723 | +0.000 |
| Assad, Javier | 72.9% | 702 | 0.729 | 0.684 | 0.684 | 0.581 | 0.708 | 0.729 | +0.000 |
| Schwellenbach, Spencer | 74.4% | 574 | 0.744 | 0.713 | 0.713 | 0.645 | 0.720 | 0.744 | +0.000 |
| Wheeler, Zack | 75.3% | 1,999 | 0.753 | 0.719 | 0.706 | 0.634 | 0.725 | 0.753 | +0.000 |
| Imanaga, Shota | 76.2% | 765 | 0.762 | 0.724 | 0.733 | 0.660 | 0.736 | 0.762 | +0.000 |
| Montas, Frankie | 76.4% | 806 | 0.764 | 0.728 | 0.717 | 0.606 | 0.760 | 0.764 | +0.000 |
| Miller, Bryce | 79.1% | 980 | 0.791 | 0.741 | 0.745 | 0.690 | 0.768 | 0.791 | +0.000 |
| Eovaldi, Nathan | 80.1% | 1,383 | 0.801 | 0.774 | 0.761 | 0.683 | 0.780 | 0.801 | +0.000 |
| Quantrill, Cal | 80.7% | 1,307 | 0.807 | 0.772 | 0.760 | 0.700 | 0.788 | 0.807 | +0.000 |
| Bradley, Taj | 84.8% | 973 | 0.848 | 0.834 | 0.833 | 0.776 | 0.825 | 0.848 | +0.000 |
| Gausman, Kevin | 90.1% | 1,844 | 0.901 | 0.882 | 0.878 | 0.825 | 0.876 | 0.901 | +0.000 |

## Confusion Matrices

<details><summary>Naive (Always Fast)</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 60349 | 0 | 0 |
| breaking | 31461 | 0 | 0 |
| off-speed | 11229 | 0 | 0 |

</details>

<details><summary>N-Gram (n=3)</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 47324 | 10450 | 2575 |
| breaking | 22763 | 7374 | 1324 |
| off-speed | 7994 | 2025 | 1210 |

</details>

<details><summary>N-Gram (n=4)</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 49472 | 8764 | 2113 |
| breaking | 24353 | 6064 | 1044 |
| off-speed | 8783 | 1480 | 966 |

</details>

<details><summary>Frequency-Based (Oracle)</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 37089 | 17298 | 5962 |
| breaking | 17298 | 11121 | 3042 |
| off-speed | 5857 | 2970 | 2402 |

</details>

<details><summary>Markov Context</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 57392 | 2421 | 536 |
| breaking | 29564 | 1647 | 250 |
| off-speed | 10740 | 265 | 224 |

</details>

<details><summary>Transformer</summary>

| Actual \ Predicted | fast | breaking | off-speed |
|-------------------|------|----------|-----------|
| fast | 57795 | 2449 | 105 |
| breaking | 27967 | 3433 | 61 |
| off-speed | 10493 | 470 | 266 |

</details>
