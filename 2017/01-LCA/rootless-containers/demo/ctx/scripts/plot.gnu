#!/usr/bin/env gnuplot

set terminal dumb;
set datafile separator ",";

# a % b
mod(a, b) = (a - (floor(a / b) * b))

# From FFT analysis.
period = 1.570103

# The data.
plot "pi.csv" using (mod($2, period)):($3);
