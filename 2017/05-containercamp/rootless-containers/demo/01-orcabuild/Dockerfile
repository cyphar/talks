# This Dockerfile can be built with https://github.com/cyphar/orca-build.git

FROM busybox

RUN whoami
RUN mkdir -p /some/directory && touch /some/file
COPY init /init
RUN chmod +x /init

ENTRYPOINT ["/init"]
CMD []
