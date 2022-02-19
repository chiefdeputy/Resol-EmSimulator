docker run   --rm   -it   \
  --name builder \
  --privileged \
  -v /root/resol-vbus:/data \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  --network=host \
  homeassistant/amd64-builder   -t /data   --amd64   --test   -i my-test-addon-{arch}   -d local
