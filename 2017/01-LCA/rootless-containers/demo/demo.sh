#!/bin/zsh
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

set -ex

# Get a copy of the root filesystem.
skopeo copy docker-daemon:cyphar/rootless-containers-demo:2017 oci:demo_image:latest
umoci unpack --rootless --image demo_image:latest demo_bundle

# Run as a rootless container.
runc --root /tmp/runc run -b demo_bundle rootless-ctr
