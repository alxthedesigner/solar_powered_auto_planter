#!/bin/sh
# Builds and runs the planter's logic tests on this computer (no ESP32 needed). Needs a C++ compiler and ArduinoJson,
# which `pio run` downloads into .pio/libdeps the first time you build the firmware. Or point ARDUINOJSON_DIR at
# ArduinoJson's src/ folder.
#   test/host/run.sh            run the tests
#   test/host/run.sh apply 2    apply settings JSON from stdin, print what the planter would use
set -e
here=$(cd "$(dirname "$0")" && pwd)
fw=$(cd "$here/../.." && pwd)
inc=${ARDUINOJSON_DIR:-$(ls -d "$fw"/.pio/libdeps/*/ArduinoJson/src 2>/dev/null | head -1)}
if [ -z "$inc" ] || [ ! -f "$inc/ArduinoJson.h" ]; then
  echo "ArduinoJson not found. Build the firmware once (pio run), or set ARDUINOJSON_DIR to ArduinoJson's src/ folder." >&2
  exit 1
fi
out=${TMPDIR:-/tmp}/planter_test
c++ -std=c++17 -Wall -Wextra -O1 -I"$inc" "$here/planter_test.cpp" -o "$out"
"$out" "$@"
