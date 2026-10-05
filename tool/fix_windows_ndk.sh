#!/usr/bin/env bash
# Prepares an Android NDK on a Windows host for the Go core and Rust helper builds.
# Usage: bash tool/fix_windows_ndk.sh /c/Android/ndk/30.0.16248370
# Idempotent. Originals of replaced wrappers are kept next to them as *.sh.bak.
set -euo pipefail
ndk="${1:?path to NDK}"
tc="$ndk/toolchains/llvm/prebuilt/windows-x86_64"
[ -d "$tc" ] || { echo "no toolchain at $tc" >&2; exit 1; }

# 1. rust_api's bindgen looks for libclang under lib/ (newer NDKs ship it only in bin/).
if [ ! -f "$tc/lib/libclang.dll" ]; then
  src=$(find "$tc" -name libclang.dll | head -n1)
  [ -n "$src" ] || { echo "libclang.dll not found in NDK: take it from the PyPI wheel libclang" >&2; exit 1; }
  cp "$src" "$tc/lib/libclang.dll"
fi

# 2. libclang on Windows resolves its builtin headers relative to the calling process,
#    so bindgen cannot find stdbool.h; give the sysroot a copy.
inc=$(ls -d "$tc"/lib/clang/*/include | head -n1)
cp -rn "$inc"/. "$tc/sysroot/usr/include/"

# 3. Go's cgo calls target-prefixed clang wrappers without an extension; on Windows those are
#    bash scripts. A hard link to clang.exe works because clang reads the target from argv[0].
n=0
for bak in "$tc"/bin/*-linux-android*-clang.sh.bak "$tc"/bin/*-linux-android*-clang++.sh.bak; do
  [ -f "$bak" ] || continue
  f="${bak%.sh.bak}"
  [ -f "$f" ] || { mv "$bak" "$f"; }
done
for f in "$tc"/bin/*-linux-android*-clang "$tc"/bin/*-linux-android*-clang++; do
  [ -f "$f" ] || continue
  if head -c 2 "$f" | grep -q '#!'; then
    case "$f" in *++) target=clang++.exe ;; *) target=clang.exe ;; esac
    [ -f "$tc/bin/$target" ] || target=clang.exe
    mv "$f" "$f.sh.bak"
    ln "$tc/bin/$target" "$f"
    n=$((n + 1))
  fi
done
echo "NDK fixed: $tc ($n wrappers linked)"
