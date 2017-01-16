#!/usr/bin/false
# keplerk2-halo: Halo Photometry of Contaminated Kepler/K2 Pixels
# Copyright (C) 2015 Aleksa Sarai <cyphar@cyphar.com>
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

import csv
import math
import warnings

import numpy

import scipy
import scipy.signal

def positions(ndarray):
	return zip(*numpy.where(numpy.ones_like(ndarray)))

def filter_img(img, track=None, frame=0):
	flxs = img[1].data["FLUX"]
	time = img[1].data["TIME"]
	qual = img[1].data["QUALITY"]
	cadn = img[1].data["CADENCENO"]
	trac = None

	# We need to fix up the times so they are in *absolute* BJD.
	time += img[1].header["BJDREFI"] + img[1].header["BJDREFF"]

	# Remove frames not in our track data.
	if track is not None:
		filt = numpy.in1d(cadn, [tr["cadence"] for tr in track])

		flxs = flxs[filt]
		time = time[filt]
		qual = qual[filt]
		cadn = cadn[filt]

		# Fix up track.
		trac = numpy.array(track)[numpy.in1d([tr["cadence"] for tr in track], cadn)]
		del track

	# Remove bad quality frames.
	filt = (qual == 0)
	flxs = flxs[filt]
	time = time[filt]
	cadn = cadn[filt]
	if trac is not None:
		trac = trac[filt]

	# Deal with NaNs.
	for flx in flxs:
		flx[numpy.isnan(flx)] = numpy.min(flx[~numpy.isnan(flx)])

	if trac is not None:
		# We set the first track as being at the given one, because then
		# the users can deal with specifiying their track point at a time t.
		trac = numpy.array([(tr["x"], tr["y"]) for tr in trac], dtype=float)
		trac[:, 0] -= trac[frame, 0]
		trac[:, 1] -= trac[frame, 1]

	return {
		"FLUX": flxs,
		"TIME": time,
		"CADENCENO": cadn,
		"TRACK": trac,
	}

def csv_column_read(f, fieldnames, casts=None, start=None, end=None, reset=False):
	if casts is None or len(fieldnames) != len(casts):
		casts = [object] * len(fieldnames)

	def parse_row(row):
		row = {k: v for k, v in row.items() if k in fieldnames}
		return [row[key] for key in sorted(row.keys(), key=lambda k: fieldnames.index(k))]

	if reset:
		pos = f.tell()

	reader = csv.DictReader(f)
	rows = [[cast(field) for cast, field in zip(casts, fields)] for fields in (parse_row(row) for row in reader)]

	if reset:
		f.seek(pos)

	return [numpy.array(col[start:end], dtype=cast) for cast, col in zip(casts, zip(*rows))]

def csv_column_write(f, cols, fieldnames):
	writer = csv.DictWriter(f, fieldnames=fieldnames)
	writer.writeheader()

	for fields in zip(*cols):
		writer.writerow({fieldnames[i]: field for i, field in enumerate(fields)})

SPINE_COLOR = "black"

def latexify(ax):
	for spine in ["top", "right"]:
		ax.spines[spine].set_visible(False)

	for spine in ["left", "bottom"]:
		ax.spines[spine].set_color(SPINE_COLOR)
		ax.spines[spine].set_linewidth(0.5)

	ax.xaxis.set_ticks_position("bottom")
	ax.yaxis.set_ticks_position("left")

	for axis in [ax.xaxis, ax.yaxis]:
		axis.set_tick_params(direction="out", color=SPINE_COLOR)

	return ax

# This generates a Lomb-Scargle periodogram in units of ppm and Hz (meaning that
# a signal of the form A * sin(2πf * t) will produce a peak at f with an amplitude
# of A).
#
# $times should be in units of days, $fluxs should be in units of ppm residuals,
# $delta should be either None or in units of µHz. The result will be a power
# spectrum in units (ppm)² per µHz. If $delta is unspecified, it will be set to
# the logically optimum Fourier sampling of (1/T) (where T is the range of $times).
# $upper should be in µHz, and a warning will be emitted if it is lower than the
# optimistic nyquist frequency (1 / (2 * median(∆t))).
#
# The returned value is a ndarray of form [frequency, spectrum] with frequencies
# in the range (0, nyquist] with spacing of $delta. Frequencies are in Hz.
def lombscargle_amplitude(times, fluxs, mult=1, upper=None):
	# Sanity checking.
	assert(fluxs.shape[0] == times.shape[0])

	# Make copies so we don't accidentally modify things outside.
	times = times.copy()
	fluxs = fluxs.copy()

	# First we need to deal with unit conversions. While we expose "logical"
	# astrophysics units, we internally need to be using µHz everywhere.
	times *= 24 * 60 * 60

	# Compute some of the parameters required for the Lomb-Scargle periodogram.
	N = fluxs.shape[0]
	T = times.ptp()

	delta = 1 / (mult * T)

	# Check against nyquist and use it as the default upper frequency.
	nyquist = N / (2 * numpy.median(numpy.diff(times)))
	if upper is None:
		upper = nyquist
	else:
		upper /= 1e6

	if upper < nyquist:
		warnings.warn("Given upper frequency (%f) for Lomb-Scargle periodogram is lower than the optimistic Nyquist frequency (%f). You may lose spectral data as a result.")

	samples = math.ceil(upper / delta)

	# Calculate a raw power spectrum. Scipy gives us an "unnormalized" power
	# spectrum, but the form of the output is known to be (A**2) * N/4, if N is
	# "large enough". It's also important to note that the $freqs parameter
	# needs to be in angular frequencies.
	freqs = numpy.linspace(delta, upper, samples)
	raw = scipy.signal.lombscargle(times, fluxs, 2 * math.pi * freqs)
	raw = numpy.sqrt(raw * (4 / N))

	return numpy.array([freqs * 1e6, raw])

# Proper calibration of Fourier transforms is **vital** in order to make results
# by different research groups work. This is a free software implementation of
# the calibration specified by the Kepler Asteroseismic Science Consortium (KASC)
# [wg1_wgmail02: appendix B]. This produces a calibrated power spectral density
# (PSD).
#
# $times should be in units of days, $fluxs should be in units of ppm residuals,
# $delta should be either None or in units of µHz. The result will be a power
# spectrum in units (ppm)² per µHz. If $delta is unspecified, it will be set to
# the logically optimum Fourier sampling of (1/T) (where T is the range of $times).
#
# The returned value is a ndarray of form [frequency, spectrum] with frequencies
# in the range (0, nyquist] with spacing of $delta. The spectrum will be scaled
# according to the specified standard [wg1_wgmail02: appendix B]. Frequencies are
# in Hz.

# Converts a raw (amplitude) periodogram to a calibrated PSD according to the
# description in [wg1_wgmail02: appendix B].
def raw_to_psd(freqs, raw, variance):
	# Amplitude -> Power
	raw = raw ** 2

	# Scale power spectrum.
	# ppm^2 * (ppm^2 / ppm^2) / µHz
	scaled = raw * variance / (raw.sum() * numpy.diff(freqs).mean())
	return numpy.array([freqs, scaled])
