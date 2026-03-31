# syntax=docker/dockerfile:1.7
# Blackwell-friendly training image for heavy LoRA fine-tuning and post-training NVFP4 compilation.
FROM nvidia/cuda:13.1.0-devel-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV MODELOPT_DIR=/opt/Model-Optimizer
ENV VIRTUAL_ENV=/opt/venv
ENV PATH=/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_PREFER_BINARY=1
ENV FILEBROWSER_PORT=8080
ENV FILEBROWSER_ROOT=/workspace
ENV RUNPOD_USER=runpod
ENV RUNPOD_PASSWORD=runpod

ARG FILEBROWSER_VERSION=v2.32.0
ARG SKIP_FLASH_ATTN_AT_BUILD=1

WORKDIR /workspace

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
	--mount=type=cache,target=/var/lib/apt,sharing=locked \
	apt-get update && apt-get install -y --no-install-recommends \
	bash \
	build-essential \
	ca-certificates \
	curl \
	adduser \
	git \
	git-lfs \
	ninja-build \
	openssh-server \
	python3 \
	python3-dev \
	python3-pip \
	python3-venv \
	tini \
	&& rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/local/bin/python && \
	ln -sf /usr/bin/pip3 /usr/local/bin/pip

RUN python3 -m venv ${VIRTUAL_ENV} && \
	${VIRTUAL_ENV}/bin/python -m pip install --upgrade pip setuptools wheel

RUN curl -fsSL "https://github.com/filebrowser/filebrowser/releases/download/${FILEBROWSER_VERSION}/linux-amd64-filebrowser.tar.gz" \
	| tar -xz -C /usr/local/bin filebrowser

RUN mkdir -p /var/run/sshd /workspace/.filebrowser && \
	if ! id -u ${RUNPOD_USER} >/dev/null 2>&1; then /usr/sbin/adduser --disabled-password --gecos "" ${RUNPOD_USER}; fi && \
	chown -R ${RUNPOD_USER}:${RUNPOD_USER} /workspace

RUN git clone --depth=1 https://github.com/NVIDIA/Model-Optimizer.git ${MODELOPT_DIR}

COPY ./setup-train-runpod/embed_dataset.py /workspace/embed_dataset.py
COPY ./setup-train-runpod/install-blackwell-stack.sh /workspace/install-blackwell-stack.sh
COPY ./setup-train-runpod/requirements-train.txt /workspace/requirements-train.txt
COPY ./setup-train-runpod/start-runpod-services.sh /usr/local/bin/start-runpod-services.sh
COPY ./setup-train-runpod/train.py /workspace/train.py

RUN chmod +x /workspace/install-blackwell-stack.sh /usr/local/bin/start-runpod-services.sh
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
	SKIP_FLASH_ATTN=${SKIP_FLASH_ATTN_AT_BUILD} /workspace/install-blackwell-stack.sh

EXPOSE 22 8080

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/start-runpod-services.sh"]
CMD ["sleep", "infinity"]
