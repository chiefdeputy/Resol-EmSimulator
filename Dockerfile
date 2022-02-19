ARG BUILD_FROM
FROM $BUILD_FROM

# Install requirements for add-on
RUN \
  apk add --no-cache \
    openjdk8-jre \
    wget \
  && wget -q -P/ https://github.com/danielwippermann/resol-vbus-java/releases/download/v0.7.0/vbus-0.7.0.jar


# Copy data for add-on
COPY run.py /
RUN chmod a+x /run.py

CMD [ "python3 /run.py" ]