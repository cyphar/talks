#!/bin/bash
# Copyright (C) 2017 SUSE LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# NOTE: This script probably doesn't make any sense if you just run it. Read
#       through it and then work through each step.

# We also assume that a demo image has been set up, which has tools like
# "tcpdump" and "ip" installed. The demo image here is called "demo_image".
# This could be done like this:
cat >Dockerfile <<EOF
FROM opensuse/amd64:42.3
RUN zypper in -y iproute2 tcpdump
EOF
docker build -t demo_image .

# 1: Namespaces+cgroups demo.
#    The key thing to show here is how you could use namespaces and cgroups by
#    themselves, what properties they provide, and then show how they exist
#    within Docker.

# Run bash inside a new {network,pid,mount} namespace.
sudo unshare -npmf bash
	mount -t proc proc /proc
	top # show that we can only see ourselves
	ip addr # show that we can only see a loopback device

# Create a new cgroup, join it, then try to forkbomb.
sudo -s
	cat /proc/self/cgroup # show what cgroups exist
	ls -l /sys/fs/cgroup # show where cgroups live
	mkdir -p /sys/fs/cgroup/pids/our_demo_cgroup
	echo $$ > /sys/fs/cgroup/pids/our_demo_cgroup/cgroup.procs
	echo 128 > /sys/fs/cgroup/pids/our_demo_cgroup/pids.max
	:() { :|: & };: # show that forkbombs don't work

# Show the same thing as above with Docker.
docker run --rm --pids-limit=128 -it demo_image bash
	top # show that we can only see ourselves
	ip addr # show that we can only see a loopback device
	:() { :|: & };: # show that forkbombs don't work

# 2: Capabilities.
#    The main thing we're showing here is that certain types of access are
#    restricted by capabilities. It might be helpful to skim through the man
#    page of capabilities(7) which has far more detail. We assume that the
#    host's interface is em1.

# Show that by default you *can* sniff the host's network connection, if you
# provide access to the network.
docker run --rm --net=host demo_image tcpdump -i em1

# Show that you cannot sniff the host's network connection without CAP_NET_RAW.
docker run --rm --net=host --cap-drop=net_raw demo_image tcpdump -i em1

# 3: SECCOMP.
#    Mainly we show how you could use a profile once you have one. Remember to
#    explain what the profile is, that our demo profile is a *blacklist* and
#    this is *BAD*, and that the default Docker profile is a *whitelist* which
#    you should base new profiles off. It should also be noted that the default
#    Docker profile actually adds additional capability-based restrictions for
#    syscalls which is pretty cool.

# Show that mkdir works with the default profile.
docker run --rm demo_image mkdir /something

# Show that mkdir fails with our new profile.
docker run --rm --security-opt seccomp=seccomp.json demo_image mkdir /something

# 4: AppArmor
#    We mainly show what sort of things you can block with AppArmor that you
#    couldn't block with seccomp (pathname matching and so on). The default
#    AppArmor profile actually protected against CVE-2017-16539 (it's not
#    possible to write to /proc/scsi/** even with CAP_DAC_OVERRIDE).

# Load the profile (this is required). You can show it doesn't work without
# this by doing an 'apparmor_parser -R apparmor.prof'.
sudo apparmor_parser -a apparmor.prof

# Run a container with the default AppArmor profile.
docker run --rm demo_image mkdir /etc/whatever

# Run a container with our profile that blocks /etc write-and-execute access.
# Note that the profile name is the name of the profile loaded (not the
# filename).
docker run --rm --security-opt apparmor=susecon2017 -it demo_image bash
	mkdir /etc/whatever # fails
	mkdir /etc/opt/whatever # fails
	mkdir /etca # works
	mkdir /whatever # works

# THAT'S ALL FOLKS!
