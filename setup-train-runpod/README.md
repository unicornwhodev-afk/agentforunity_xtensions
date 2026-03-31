# AgentUnity — RunPod Fine-Tuning and Blackwell NVFP4 Compilation

This setup prepares a Unity code dataset, fine-tunes Qwen 3.5 family checkpoints with LoRA, merges the fine-tuned adapter into a full checkpoint, and can compile that fine-tuned checkpoint for Blackwell deployment with NVFP4 KV cache.

The base image now uses CUDA `13.1` tooling and the Docker build installs the full Blackwell training stack directly into the image.

The training image now starts a utility service by default for RunPod-style access:

- File Browser on port `8080`

Default credentials are controlled by `RUNPOD_USER` and `RUNPOD_PASSWORD`. Override them in the pod template. (RunPod natively manages SSH connections directly through its dashboard, so no custom SSH daemon is required).

## Supported training targets

The training script exposes three presets sized for this project:

| Preset | Base model | Typical use |
|---|---|---|
| `qwen3.5-4b` | `Qwen/Qwen3-4B-Instruct-2507` | Fast iteration and lower-cost experiments |
| `qwen3.5-9b` | `Qwen/Qwen3-8B-Instruct-2507` | Balanced quality and training cost |
| `qwen3.5-14b` | `Qwen/Qwen3-14B-Instruct-2507` | Heavy Blackwell pod training and best final quality |

`qwen3.5-14b` is the default preset for heavy RunPod training.

## Pipeline overview

The end-to-end flow is split into three stages:

1. **Data preparation on CPU**
     Downloads selected repositories, cleans Unity source code, and emits `resources.json` plus `files_index.json`.

2. **Embedding and LoRA fine-tuning on GPU**
     Generates embeddings for the prepared dataset and fine-tunes a Qwen 3.5 preset with LoRA on the cleaned files.

3. **Post-training merge and NVFP4 compilation**
     Merges the fine-tuned LoRA adapter into a standalone Hugging Face checkpoint, then runs offline quantization so the fine-tuned model can be deployed on Blackwell with NVFP4 KV cache.

## Build the images

```bash
docker build -f setup-train-runpod/data-prep.Dockerfile -t YOUR_DOCKERHUB_USERNAME/agentunity-dataprep:latest .
docker push YOUR_DOCKERHUB_USERNAME/agentunity-dataprep:latest

docker build -f setup-train-runpod/training.Dockerfile -t YOUR_DOCKERHUB_USERNAME/agentunity-training:latest .
docker push YOUR_DOCKERHUB_USERNAME/agentunity-training:latest
```

## Prepare the dataset

```bash
mkdir -p ./Unity-Dataset

docker run --rm \
    -v "$(pwd)/Unity-Dataset:/dataset" \
    -v "$(pwd):/workspace" \
    YOUR_DOCKERHUB_USERNAME/agentunity-dataprep:latest \
    python /app/prepare_dataset.py \
        --dataset-path /dataset \
        --resources-path /workspace/setup-train-runpod/train
```

After completion, `Unity-Dataset` contains `raw/`, `cleaned/`, and `metadata/`.

## Recommended RunPod template

For the heavy training path, target a Blackwell pod such as RTX PRO 6000 Blackwell.

| Setting | Value |
|---|---|
| Template name | `AgentUnity Qwen Training` |
| Container image | `YOUR_DOCKERHUB_USERNAME/agentunity-training:latest` |
| GPU type | `RTX PRO 6000 Blackwell` |
| GPU count | `1` for 4B and 9B, `2` preferred for 14B |
| Volume mount path | `/workspace` |
| Container disk | `60 GB` minimum |

Recommended environment variables:

| Variable | Example |
|---|---|
| `HF_TOKEN` | `hf_...` |
| `MODEL_PRESET` | `qwen3.5-14b` |
| `NEW_MODEL_NAME` | `AgentUnity-Qwen35-14B` |
| `EXPORT_NVFP4` | `1` |
| `RUNPOD_USER` | `runpod` |
| `RUNPOD_PASSWORD` | `change-me` |

The image build runs the following bootstrap script during `docker build`:

```bash
/workspace/install-blackwell-stack.sh
```

This installs the full GPU training stack into the image, including PyTorch, Transformers, TRL, BitsAndBytes, `flash-attn`, and `nvidia-modelopt[torch]`.

During `docker build`, `flash-attn` is skipped by default to avoid expensive native compilation in the image build. If you want it later inside the running pod, run:

```bash
SKIP_FLASH_ATTN=0 /workspace/install-blackwell-stack.sh
```

Important note: the container toolkit is CUDA `13.1`, but PyTorch stable currently publishes wheels up to `cu130` in the upstream selector. The install script therefore defaults to the `cu130` wheel index unless you override `PYTORCH_INDEX_URL` with a newer upstream index.

## Run jobs in the pod

Generate embeddings first:

```bash
python /workspace/embed_dataset.py \
    --dataset-path /workspace/Unity-Dataset \
    --batch-size 32
```

Then fine-tune and compile the fine-tuned model:

```bash
accelerate launch /workspace/train.py \
    --dataset-path /workspace/Unity-Dataset \
    --model-output-path /workspace/models \
    --model-preset qwen3.5-14b \
    --export-nvfp4
```

## Local build with 15 GB RAM

For a machine with around 15 GB RAM available, use BuildKit and keep the build constrained to the lighter image path:

```bash
docker build \
    --file setup-train-runpod/training.Dockerfile \
    --tag agentunity-training:local \
    --memory=12g \
    --build-arg BUILDKIT_INLINE_CACHE=1 \
    .
```

This image is optimized for local build by:

1. Using a reduced Docker build context via `.dockerignore`
2. Using cache mounts for `apt` and `pip`
3. Keeping the heavy CUDA-sensitive stack prebuilt inside the final image for direct pod startup

## Output layout

For a run named `AgentUnity-Qwen35-14B`, artifacts are saved as:

```text
/workspace/models/AgentUnity-Qwen35-14B/
    adapter/
    merged/
    trtllm_nvfp4/
```

## Important clarification on NVFP4

The NVFP4 step targets the fine-tuned model, not the original base checkpoint.

The script performs this exact order:

1. Train the LoRA adapter.
2. Merge the adapter into the base model.
3. Quantize the merged fine-tuned checkpoint.
4. Emit TensorRT-LLM-oriented deployment artifacts with NVFP4 KV cache support.

This keeps the deployment artifact aligned with the learned weights instead of quantizing only the untouched base model.
