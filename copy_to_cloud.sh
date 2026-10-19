#!/usr/bin/env bash
# copy_to_cloud.sh
# Asks for your Neon connection string (hidden, nothing shows on screen and it isn't saved anywhere),
# then copies your Krypton account and portfolio into the online database (see copy_to_cloud.py).
#
# Run it with:   bash copy_to_cloud.sh

echo "Paste your Neon connection string and press Enter."
echo "(Nothing will appear while you paste. That's normal, it's hidden on purpose.)"
read -r -s -p "> " URL
echo
URL="$(echo -n "$URL" | tr -d '[:space:]')"   # remove accidental spaces or line breaks

if [[ "$URL" != postgres* ]]; then
    echo "❌ That doesn't look like a Neon connection string (it should start with postgresql://). Nothing was copied."
    exit 1
fi

cd "$(dirname "$0")"
DATABASE_URL="$URL" python copy_to_cloud.py
unset URL
