#!/usr/bin/env bash

set -euxo pipefail

# Launch `mitmdump` with `sniffer.py` as the add-on script.
mitmdump -qs sniffer.py &
# Wait for `mitmdump` to complete launching.
sleep 15

# Once `mitmdump` is launched, the `~/.mitmproxy` directory is created.
# Copy the mitmproxy certificate created there.
openssl x509 -in ~/.mitmproxy/mitmproxy-ca-cert.pem -inform PEM -out ~/mitmproxy-ca-cert.crt

# Launch the headless Chrome and close it immediately.
python3 launch-and-close-chrome.py

# Once Google Chrome is launched, the `~/.pki/nssdb` directory is created.
# Copy the mitmproxy's certificate to the certificate store created there.
certutil -A -n mitmproxy -t 'TCu,Cu,Tu' -i ~/mitmproxy-ca-cert.crt -d "sql:$HOME/.pki/nssdb"

# Launch fetcher.
python3 fetcher.py
