FROM opensuse/amd64:42.2

RUN zypper ar -f obs://devel:languages:python3 obs-py3k && \
	zypper rr NON-OSS "Update Non-Oss" && \
	zypper --no-gpg-check up -y && \
	zypper in -y curl gnuplot python3-{scipy,numpy,shapely,astropy,matplotlib}

COPY . /
