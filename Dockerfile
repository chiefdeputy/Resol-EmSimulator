ARG BUILD_FROM=ghcr.io/hassio-addons/debian-base/amd64:5.2.3
# hadolint ignore=DL3006
FROM ${BUILD_FROM}

# Confiure locale
#ENV \
#    LANG=en_US.UTF-8 \
#    LANGUAGE=en_US:en \
#    LC_ALL=en_US.UTF-8

# Set shell
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Setup base system
ARG BUILD_ARCH=amd64

RUN \
  apt-get update \
  # && apt-get install -y --no-install-recommends \
  #   wget \
  #   apt-transport-https \
  #   gnupg software-properties-common \
  # && wget -qO - https://adoptopenjdk.jfrog.io/adoptopenjdk/api/gpg/key/public | apt-key add - \
  # && add-apt-repository --yes https://adoptopenjdk.jfrog.io/adoptopenjdk/deb/ \
  # && apt-get update \
  && apt-get install -y --no-install-recommends \
    # adoptopenjdk-8-hotspot \
    openjdk-11-jdk-headless \
    wget \
    python3 \
    python3-pip \
    python3-dev \
    cython3 \
    gcc \
  && wget -q -O /root/vbus.jar https://github.com/danielwippermann/resol-vbus-java/releases/download/v0.9.0/vbus-0.9.0.jar \
  && pip install pyjnius aiohttp websockets \
  && apt-get remove --purge -y \
    wget \
    apt-transport-https \
    gnupg software-properties-common \
    python3-dev \
    gcc \
    cython3 \
  && apt-get autoremove --purge -y

ENV PYTHONUNBUFFERED=1
ENV S6_LOGGING=0
ENV JAVA_CLASSES=/root/vbus.jar
ENV CONFIG=/data/options.json
ENV BUILD_VERSION=${BUILD_VERSION}

# add local files
COPY rootfs/ /
 