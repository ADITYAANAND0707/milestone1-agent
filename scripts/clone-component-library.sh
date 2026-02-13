#!/bin/sh
# Clone Untitled UI Nextjs starter kit as the component library
REPO="https://github.com/untitleduico/untitledui-nextjs-starter-kit.git"
TARGET="$(dirname "$0")/../component-library"
if [ -d "$TARGET" ]; then
  echo "component-library exists. Pulling latest..."
  (cd "$TARGET" && git pull)
else
  echo "Cloning Untitled UI starter kit to component-library..."
  git clone "$REPO" "$TARGET"
fi
echo "Done. Component library at: $TARGET"
