FROM sitespeedio/browsertime:14.8.0
USER root

RUN apt-get update && apt-get install -y \
  iputils-ping \
  dnsutils \
  nano \
  libnss3-tools

RUN [ -d ~/.pki/nssdb ] || mkdir -p ~/.pki/nssdb

RUN rm -r /opt/google/chrome/*

COPY ../browsertime/docker/chromium/src/out/Default /opt/google/chrome

RUN chown -R root:root /opt/google/chrome

COPY ../../setup/certificates/RootCA.cert /root/ca.crt
COPY ./lighthouse-xvfb.sh /usr/local/bin/lighthouse-xvfb.sh

RUN certutil -d sql:/root/.pki/nssdb -A -n 'example ca' -i /root/ca.crt -t TCP,TCP,TCP

# Install 'n' to manage Node.js versions
RUN npm install -g n

# Update Node.js to the latest version using 'n'
RUN n stable

# Clear the cache to keep the container clean
RUN npm cache clean --force

# Install Lighthouse globally (old lighthouse version for Chrome 95)
RUN npm install -g lighthouse@8.4.0
