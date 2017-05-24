```
% # skopeo copy docker://cyphar/rootless-containers-demo:2017 oci:image
% skopeo copy docker-archive:demo-whale.img oci:image
% umoci unpack --rootless --image image bundle
% runc --root /tmp/runc run -b bundle ctr
# ...
```
