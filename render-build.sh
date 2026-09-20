#!/usr/bin/env bash
set -e

# Moon Bot v2｜Render Build
# 安裝 Python 套件 + yt-dlp 所需的 Deno JavaScript runtime

pip install -r requirements.txt

DENO_INSTALL="$PWD/.deno"
export DENO_INSTALL

if [ ! -x "$DENO_INSTALL/bin/deno" ]; then
    curl -fsSL https://deno.land/install.sh | sh
fi

"$DENO_INSTALL/bin/deno" --version
