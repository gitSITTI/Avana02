#!/bin/sh
# Bundle Excalidraw's exporter into one browser script (about 20 MB, so it is not shipped; rebuild it).
set -e
cd "$(dirname "$0")"
npx esbuild entry.js --bundle --format=iife --platform=browser --outfile=bundle.js --define:process.env.NODE_ENV='"production"' --log-level=warning
ls -la bundle.js
