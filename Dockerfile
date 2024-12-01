FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/Vienna
RUN apt update && apt -y --no-install-recommends upgrade
RUN apt install --no-install-recommends -y \
    tzdata \
    python3-setuptools \
    python3-pip \
    python3-requests \
    python3-yaml \
    python3-boto3 \
    python3-dateutil

WORKDIR /usr/src/app
RUN mkdir /usr/src/app/data && chown -R ubuntu /usr/src/app
COPY ./build/requirements.txt /usr/src/app/
COPY ./build/webstorageS3-1.2.1-py3-none-any.whl /usr/src/app/
# install python modules
RUN pip3 install --break-system-packages --disable-pip-version-check --no-cache-dir ./webstorageS3-1.2.1-py3-none-any.whl
RUN pip3 install --break-system-packages --disable-pip-version-check --no-cache-dir -r requirements.txt
RUN pip3 freeze

# cleanup
# starting at 471MB
# with updates 473MB
# down to 227MB
RUN apt -y purge python3-pip python3-setuptools; \
    apt -y autoremove; \
    apt -y clean; rm /usr/src/app/webstorageS3-1.2.1-py3-none-any.whl

# to use webstorage
RUN mkdir /home/ubuntu/.webstorage
COPY ./secret/webstorage.yml /home/ubuntu/.webstorage/webstorage.yml
# to access google fotos
COPY ./secret/credentials.json /usr/src/app/credentials.json
COPY ./secret/photoslibrary.pickle /usr/src/app/photoslibrary.pickle

# the main programs
COPY ./build/tools.py /usr/src/app/tools.py
COPY ./build/main.py /usr/src/app/main.py

RUN chown -R ubuntu /usr/src/app
USER ubuntu
CMD ["python3", "/usr/src/app/main.py"]
