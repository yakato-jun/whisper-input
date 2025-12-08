#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "This setup script is for Linux only."
  exit 1
fi

APT_PKGS=("xdotool" "xclip" "portaudio19-dev")
PYTHON=${PYTHON:-python3}
VENV_DIR=".venv"

apt_get() {
  if command -v apt-get >/dev/null 2>&1; then
    if command -v sudo >/dev/null 2>&1; then
      sudo apt-get "$@"
    else
      apt-get "$@"
    fi
  else
    echo "apt-get not found. Install ${APT_PKGS[*]} manually and rerun." >&2
    exit 1
  fi
}

echo "Installing system packages: ${APT_PKGS[*]}"
apt_get update
apt_get install -y "${APT_PKGS[@]}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "python3 is required." >&2
  exit 1
fi

echo "Creating virtual environment at ${VENV_DIR}"
"$PYTHON" -m venv "$VENV_DIR"
# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"

echo "Upgrading pip and installing Python dependencies"
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete. Export OPENAI_API_KEY and run: source ${VENV_DIR}/bin/activate && python main.py"
