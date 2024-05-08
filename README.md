Adapting Aaronson's Oracle to predict a starting pitcher's next baseball pitch.


## Pseudo-code

1. Fetch pitch by pitch log
1. Initialize a dictionary that will store a n-gram combination as the key and the number of times each pitch type that follows this n-gram combination as dict of values
1. Record the rolling n-gram combination as you loop through the pitch log
1. Look up the highest pitch type value, return that or default to one by chance if there are no stored values
1. Update the dictionary with the actual next pitch

## Statscast Pitch Types

CH: changeup
CU: curveball
FC: cutter 
EP: eephus
FO: forkball 
FF: four-seam fastball 
KN: knuckleball 
KC: knuck curve
SC: screwball
SI: sinker
SL: slider
SV: slurve
FS: splitter 
ST: sweeper