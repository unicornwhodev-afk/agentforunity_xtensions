#!/usr/bin/env bash
set -euo pipefail

RUNPOD_USER="${RUNPOD_USER:-runpod}"
RUNPOD_PASSWORD="${RUNPOD_PASSWORD:-runpod}"
FILEBROWSER_PORT="${FILEBROWSER_PORT:-8080}"
FILEBROWSER_ROOT="${FILEBROWSER_ROOT:-/workspace}"
FILEBROWSER_DB="${FILEBROWSER_DB:-/workspace/.filebrowser/filebrowser.db}"
FILEBROWSER_CONFIG="${FILEBROWSER_CONFIG:-/workspace/.filebrowser/settings.json}"
AUTHORIZED_KEYS="${PUBLIC_KEY:-${AUTHORIZED_KEYS:-}}"

mkdir -p /var/run/sshd /workspace/.filebrowser

if ! id -u "${RUNPOD_USER}" >/dev/null 2>&1; then
    /usr/sbin/adduser --disabled-password --gecos "" "${RUNPOD_USER}"
fi

echo "${RUNPOD_USER}:${RUNPOD_PASSWORD}" | chpasswd
mkdir -p "/home/${RUNPOD_USER}/.ssh"
chmod 700 "/home/${RUNPOD_USER}/.ssh"

if [ -n "${AUTHORIZED_KEYS}" ]; then
    printf '%s\n' "${AUTHORIZED_KEYS}" > "/home/${RUNPOD_USER}/.ssh/authorized_keys"
    chmod 600 "/home/${RUNPOD_USER}/.ssh/authorized_keys"
    chown -R "${RUNPOD_USER}:${RUNPOD_USER}" "/home/${RUNPOD_USER}/.ssh"
fi

sed -i 's/^#\?PasswordAuthentication .*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/^#\?PermitRootLogin .*/PermitRootLogin no/' /etc/ssh/sshd_config
sed -i 's/^#\?PubkeyAuthentication .*/PubkeyAuthentication yes/' /etc/ssh/sshd_config

/usr/sbin/sshd

filebrowser config init \
    --address 0.0.0.0 \
    --port "${FILEBROWSER_PORT}" \
    --root "${FILEBROWSER_ROOT}" \
    --database "${FILEBROWSER_DB}" \
    --config "${FILEBROWSER_CONFIG}" >/dev/null 2>&1 || true

if ! filebrowser users ls --database "${FILEBROWSER_DB}" 2>/dev/null | grep -q "${RUNPOD_USER}"; then
    filebrowser users add "${RUNPOD_USER}" "${RUNPOD_PASSWORD}" \
        --perm.admin \
        --database "${FILEBROWSER_DB}" >/dev/null
fi

filebrowser \
    --database "${FILEBROWSER_DB}" \
    --config "${FILEBROWSER_CONFIG}" >/tmp/filebrowser.log 2>&1 &

exec "$@"