```
% orca-build -t latest --output image .
# ...
% umoci unpack --rootless --image image bundle
% runc --root /tmp/runc run -b bundle ctr
```
