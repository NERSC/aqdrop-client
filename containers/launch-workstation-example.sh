#!/bin/bash
set -e  # Exit immediately on any error

source ~/.ssh/aqdrop_user.creds

IMG=aqdrop-client:latest

echo launch image $IMG
echo you are launching Podman image ... remember to exit

JNB_PORT=''
BASE_DIR=/shared_volumes/myAQDrop/AQDrop   # here git has home
WORK_DIR=/AQDrop/examples
DATA_VAULT=/shared_volumes/dataVault2026

echo "The number of arguments is: $#"
#  encoded variables:    jnb
PORT=8834
for var in "$@"; do
  echo "The length of argument '$var' is: ${#var}"
  if [[ "jnb" ==  $var ]];  then
      JNB_PORT="-p  ${PORT}:${PORT}"
      echo added  $JNB_PORT
      echo " EXEC:    jupyter notebook --ip 0.0.0.0 --no-browser --allow-root --port  $PORT "
  fi
  # ... more ...
done


eval podman run -it \
     -e SFAPI_TOKEN=$SFAPI_TOKEN \
     -e AQDROP_HOSTNAME=$AQDROP_HOSTNAME \
    --volume /shared_volumes/quantumMind:/quantumMind \
    --volume $DATA_VAULT:/dataVault2026 \
    --volume $BASE_DIR:/AQDrop \
    -e DISPLAY=host.containers.internal:0  \
    --workdir $WORK_DIR $JNB_PORT \
    --entrypoint /bin/bash \
    $IMG
