# README

Adapting [Aaronson's Oracle](https://github.com/elsehow/aaronson-oracle/blob/master/README.md) to predict a starting pitcher's next baseball pitch.

The idea is to use a simple algorithm of remembering the most probable next thing given the past n combinations to make a *surprisingly* good prediction.z

## Pseudo-code

1. Fetch a starting pitchers game's pitch by pitch log using `pybaseball`
    * Gets Statscast data which categorizes each pitch type
1. Initialize a dictionary that will store a n-gram combination as the key and the number of times each pitch type that follows this n-gram combination as dict of values
1. Record the rolling n-gram combination as you iterate through the pitch log
1. Update the dictionary with the actual next pitch
1. Look up the highest pitch type value, return that or default to one by chance if there are no stored values as the prediction

## Statscast Pitch Types

* CH: changeup
* CU: curveball
* FC: cutter
* EP: eephus
* FO: forkball
* FF: four-seam fastball
* KN: knuckleball
* KC: knuck curve
* SC: screwball
* SI: sinker
* SL: slider
* SV: slurve
* FS: splitter
* ST: sweeper

Convert to three categories of "fast", "breaking", "off-speed".

## Run

`python app.py` and navigate to <http://127.0.0.1:5000>

## TODO

* [ ] How does the naive prediction do, guess "fast" for all
* [ ] How does random guessing with weighted percentages do
* [ ] Calculate the rolling prediction
