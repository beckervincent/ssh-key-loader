#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

NAME=ssh-key-loader
VERSION="$(sed -n 's/^Version:[[:space:]]*//p' "$NAME.spec")"
OUT="${HOME}/rpmbuild/SOURCES"
mkdir -p "$OUT"

PREFIX="$NAME-$VERSION"
git archive --format=tar.gz --prefix="$PREFIX/" -o "$OUT/$PREFIX.tar.gz" HEAD 2>/dev/null \
    || tar --transform "s,^,$PREFIX/," -czf "$OUT/$PREFIX.tar.gz" \
        src data Makefile README.md LICENSE "$NAME.spec"

echo "Wrote $OUT/$PREFIX.tar.gz"
