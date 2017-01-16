#!/bin/sh
# demo: demo for rootless-containers-2017 talk at LCA
# Copyright (C) 2016 Aleksa Sarai <asarai@suse.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Get the pixel file -- demonstrate networking.
echo "[*] Downloading pi Sco star data..."
#curl -o- https://archive.stsci.edu/missions/k2/target_pixel_files/c2/203400000/42000/ktwo203442993-c02_lpd-targ.fits.gz | gzip -d > data/ktwo203442993-c02_lpd-targ.fits
curl -o data/ap_203442993.txt https://raw.githubusercontent.com/cyphar/keplerk2-halo/master/data/pi_Sco/1.203442993/ap_203442993.txt
curl -o data/xy_203442993.csv https://raw.githubusercontent.com/cyphar/keplerk2-halo/master/data/pi_Sco/1.203442993/xy_203442993.csv

# Run the analysis.
echo "[*] Halo photometric analysis..."
./scripts/clever.py --csv -s halo.csv \
    -mf 400 -m data/ap_203442993.txt \
	-d 1 -t data/xy_203442993.csv \
    data/ktwo203442993-c02_lpd-targ.fits

echo "[*] Highpass filtering..."
./scripts/highpass.py -o 6 -w 201 -sc 50 -ec -580 -s pi.csv halo.csv

# Plot.
echo "[*] Plotting output..."
./scripts/plot.gnu
