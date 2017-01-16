#!/usr/bin/env python3
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

# This is an implementation of what we hope to be a working method we are
# exploring in this project.

# The key magic sauce of this method is that we create an aperture to contain
# the contamination pixels we are interested in, and then weigh the pixel sum
# by the area intersections of the aperture polygon with the pixel grid.

# Using tracking data (created using a-priori information about the telescopes
# rotational motion, courtesy of Ben Pope), we move the aperture polygon to
# ensure the weighting of the pixel sum tracks the contamination pixels on a
# sub-pixel basis.

# The main issue here is trying to deal with the systematics of K2, because we
# don't have the luxury of having apertures larger than the important pixels.
# All pixels are important and we want to discard as few as possible, so we're
# going to have to come up with something better than that. The larger the
# systematics, the worse our output will be. However, the data we are interested
# in *is* in the data sets. We just have to tease it out, by any means necessary.

# It seems as though certain apertures (ones that do not intersect with any
# bright pixels at the edges, and don't ever leave the frame) manage to
# *entirely* remove the pointing systematics from the Fourier transform. But
# this isn't always possible, so we need to come up with some other technqiues
# to find the signal in the noise.

import os
import csv
import sys
import math
import argparse
import warnings

import astropy as ap
import astropy.io.fits

import matplotlib as mpl
if "--animate" in sys.argv or "--ani" in sys.argv:
	mpl.use("TkAgg") # Hack to fix OS X.
if not os.getenv("DISPLAY"):
	mpl.use("Agg") # Hack to fix no display.
import matplotlib.pyplot as plt
import matplotlib.animation

import numpy as np
import scipy as sp

import shapely as shp
import shapely.ops
import shapely.affinity
import shapely.geometry

import utils

DEFAULT_CROP_FRACTION = 0.2

def percentile_sample(sample, pmin=1.0, pmax=95.0):
	with warnings.catch_warnings():
		warnings.filterwarnings('ignore', message="(.*)invalid value(.*)")
		return np.percentile(sample[sample > 0], [pmin, pmax])

# XXX: I don't like the fact that we pregenerate the dithered pixels and then
#      pass them to smoother. Surely there's a nicer method.

def pixels(shape, config):
	pxs = np.empty(shape, dtype=object)

	for x, y in utils.positions(pxs):
		pxs[x, y] = shp.geometry.box(x - config.dither, y - config.dither, x + config.dither, y + config.dither)

	return pxs

def smoother(aperture, pxs, config):
	smooth = np.zeros_like(pxs, dtype=float)

	for x, y in utils.positions(smooth):
		smooth[x, y] = pxs[x, y].intersection(aperture).area

	return smooth

def out_csv(flximg, aperture, config):
	FIELDS = ["cadence", "t", "flux", "x", "y"]

	flxs = flximg["FLUX"]
	time = flximg["TIME"]
	cadn = flximg["CADENCENO"]
	trac = flximg["TRACK"]

	xs = time
	ys = []

	pxs = pixels(flxs.shape[1:], config)
	for i, flx in enumerate(flxs):
		# XXX: Output some information to convince people we haven't frozen.
		sys.stdout.write(".")
		sys.stdout.flush()

		# Smooth and weight using the aperture.
		_aperture = shp.affinity.translate(aperture, *-trac[i])
		flx *= smoother(_aperture, pxs, config)

		# TODO: We need to allow certain percentiles rather than just summing.
		#       The only question is whether that would by physically valid.
		ys.append(np.sum(flx))

	sys.stdout.write("DONE\n")
	sys.stdout.flush()

	# Save photometry data.
	with open(config.ofile, "w", newline='') as cfile:
		utils.csv_column_write(cfile, [cadn, time, ys, trac[:,0], trac[:,1]], fieldnames=FIELDS)

# XXX: We **REALLY** don't need this **AT ALL**.
#      It needs to be killed so we can make the rest of the code useful.
def plot_ani(fig, flximg, aperture, config):
	flxs = flximg["FLUX"]
	trac = flximg["TRACK"]
	vmin, vmax = percentile_sample(flxs)

	ax = fig.add_subplot(111)
	ax.set_title("Centroid Tracking and Annulus Animation")
	ax.set_xlim(left=-0.5, right=flxs.shape[1]-0.5)
	ax.set_ylim(bottom=-0.5, top=flxs.shape[2]-0.5)
	im = ax.matshow(np.zeros(flxs.shape[1:]), cmap="gray", norm=mpl.colors.LogNorm(vmin=vmin, vmax=vmax), origin="lower", interpolation="none")
	pl, = ax.plot([], [], "r+", mew=5, ms=40)
	txt = ax.text(0.05, 0.05, "", fontsize=26, color="w", backgroundcolor="k", transform=ax.transAxes)
	fill, = ax.plot([], [], "kx", mew=6, ms=50)

	apxs = np.zeros(flxs.shape[1:], dtype=bool)
	for x, y in utils.positions(apxs):
		apxs[x, y] = not aperture.intersection(shp.geometry.box(x, y, x + 1, y + 1)).is_empty

	pxs = pixels(flxs.shape[1:], dither=dither)
	def animate(i):
		if i >= flxs.shape[0]:
			raise StopIteration

		flx = flxs[i]

		x, y = trac[i] + np.array(flx.shape) / 2
		apy, apx = (np.array(np.where(apxs)).T - trac[i]).T

		# Smooth and weight using the aperture.
		_aperture = shp.affinity.translate(aperture, *-trac[i])
		flx *= smoother(_aperture, pxs, config)

		flx[flx == 0] = np.min(flx[flx != 0])

		im.set_array(flx)

		pl.set_data([x], [y])
		#fill.set_data(apx, apy)
		txt.set_text("Frame #%d" % (i,))

		#return [im, pl, fill, txt]
		return [im, pl, txt]

	ani = mpl.animation.FuncAnimation(fig, animate, interval=15, frames=flxs.shape[0], blit=True, repeat=False)

	if config.ofile:
		ani.save(config.ofile, writer=mpl.animation.writers['ffmpeg'](fps=15, bitrate=5000), dpi=50)
	else:
		plt.show()

# TODO: Check that we're not hitting off-by-one errors in the polygon code.
#       Looking at the animation, it looks like the mask is slightly off.
def polymask(mask):
	# XXX: Simplistic mask-to-polygon converter. No smoothing through grouping
	#      algorithms and convex hulls. It just makes a series of boxes for each
	#      selected pixel (with no weighting) and then unions them.

	SELECT_CHAR = "x"
	mask = np.array(mask, dtype=str)
	polys = []

	for x, y in zip(*np.where(mask == SELECT_CHAR)):
		px = shp.geometry.box(x, y, x + 1, y + 1)
		polys.append(px)

	return shp.ops.cascaded_union(polys)

def main(fits, config):
	with open(config.maskfile) as mfile:
		# We reverse it from the "friendly" syntax to the coordinate-correct
		# version. Should we do this? Probably not. Do we care? Nope.
		mask = [[ch for ch in line.rstrip("\n")] for line in mfile][::-1]

		# Double check that the mask is valid.
		try:
			assert len(set(len(row) for row in mask)) == 1
		except AssertionError:
			raise ValueError("mask file must have equal length lines")

		# Create polygon based on mask.
		poly = polymask(mask)

	if config.track is not None:
		with open(config.track) as tfile:
			# TODO: Fix this by using the utils version?
			def parse_row(cadence, x, y):
				return (cadence, float(x), float(y))

			# TODO: Fix this by not using fieldnames=XYZ.
			rows = csv.DictReader(tfile)

			# First row specifies the polarity.
			_, mx, my = parse_row(**next(rows))
			track = np.array([{"cadence": cadence, "x": x*mx, "y": y*my} for (cadence, x, y) in (parse_row(**row) for row in rows)])

	with ap.io.fits.open(fits) as img:
		flximg = utils.filter_img(img, track=track, frame=config.maskframe)

		# XXX: We can fix this. It looks ghastly and only exists for animate.
		fig = plt.figure(figsize=flximg["FLUX"][0].shape[::-1], dpi=50)

		if config.plot_type == "ani":
			plot_ani(fig, flximg, aperture=poly, config=config)
		elif config.plot_type == "csv":
			if not config.ofile:
				raise ValueError("Must specify --save when using --csv.")
			out_csv(flximg, aperture=poly, config=config)

if __name__ == "__main__":
	def __wrapped_main__():
		parser = argparse.ArgumentParser(description="Take a Kepler Long Cadence K2 FITS File, along with a-priori tracking data and a pre-defined aperture mask, and then do a weighted sum over each Long Cadence frame using the given aperture mask.")
		parser.add_argument("-t", "--track", dest="track", type=str, help="A CSV File with (cadence, x, y) track data of the FITS file.")
		parser.add_argument("-m", "--mask", dest="maskfile", type=str, required=True, help="Path to a mask file describing the aperture to use.")
		parser.add_argument("-mf", "--mask-frame", dest="maskframe", type=int, default=0, help="Frame number that the mask file is based on (default: 0).")
		parser.add_argument("-d", "--dither", dest="dither", type=float, default=2, help="Level of dither to mask edges.")
		parser.add_argument("-s", "--save", dest="ofile", type=str, default=None, help="The output file.")

		# XXX: We should really remove this.
		o_type = parser.add_mutually_exclusive_group(required=True)
		o_type.add_argument("--animate", dest="plot_type", action="store_const", const="ani", help="Show an animated plot of the FITS image with the (x, y) of the centroid and annulus overlayed.")
		o_type.add_argument("--csv", dest="plot_type", action="store_const", const="csv", help="Output annulus flux as a CSV file.")

		parser.add_argument("file", nargs=1)

		config = parser.parse_args()
		main(fits=config.file[0], config=config)

	__wrapped_main__()
