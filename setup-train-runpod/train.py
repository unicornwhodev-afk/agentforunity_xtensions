import argparse
import importlib.util
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import torch
from datasets import Dataset, load_dataset
from peft import LoraConfig, PeftModel, get_peft_model, prepare_model_for_kbit_training
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
from trl import SFTTrainer


MODEL_PRESETS = {
    "qwen3.5-4b": {
        "model_name": "Qwen/Qwen3-4B-Instruct-2507",
        "lora_r": 32,
        "lora_alpha": 64,
        "batch_size": 8,
        "gradient_accumulation_steps": 4,
        "learning_rate": 2e-4,
        "max_seq_length": 4096,
    },
    "qwen3.5-9b": {
        "model_name": "Qwen/Qwen3-8B-Instruct-2507",
        "lora_r": 48,
        "lora_alpha": 96,
        "batch_size": 4,
        "gradient_accumulation_steps": 8,
        "learning_rate": 1.5e-4,
        "max_seq_length": 4096,
    },
    "qwen3.5-14b": {
        "model_name": "Qwen/Qwen3-14B-Instruct-2507",
        "lora_r": 64,
        "lora_alpha": 128,
        "batch_size": 2,
        "gradient_accumulation_steps": 16,
        "learning_rate": 1e-4,
        "max_seq_length": 4096,
    },
}

DEFAULT_TARGET_MODULES = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]


@dataclass
class TrainConfig:
    preset_name: str
    model_name: str
    new_model_name: str
    max_seq_length: int
    batch_size: int
    gradient_accumulation_steps: int
    learning_rate: float
    lora_r: int
    lora_alpha: int
    epochs: int
    export_nvfp4: bool
    quantize_base: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fine-tune a Qwen code model on the Unity dataset and optionally compile the merged checkpoint for NVFP4 deployment."
    )
    parser.add_argument("--dataset-path", type=str, required=True, help="Path to the root of the dataset directory.")
    parser.add_argument("--model-output-path", type=str, required=True, help="Path to save the trained model artifacts.")
    parser.add_argument(
        "--model-preset",
        type=str,
        choices=sorted(MODEL_PRESETS.keys()),
        default=os.getenv("MODEL_PRESET", "qwen3.5-14b"),
        help="Target preset for the base model.",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=int(os.getenv("TRAIN_EPOCHS", "1")),
        help="Number of fine-tuning epochs.",
    )
    parser.add_argument(
        "--max-seq-length",
        type=int,
        default=int(os.getenv("MAX_SEQ_LENGTH", "0")),
        help="Override preset max sequence length. 0 keeps the preset value.",
    )
    parser.add_argument(
        "--export-nvfp4",
        action="store_true",
        default=os.getenv("EXPORT_NVFP4", "0") == "1",
        help="Merge the fine-tuned adapter into a full checkpoint and quantize it for NVFP4-capable Blackwell deployment.",
    )
    parser.add_argument(
        "--skip-base-4bit",
        action="store_true",
        help="Disable 4-bit loading during LoRA fine-tuning.",
    )
    return parser.parse_args()


def build_train_config(args: argparse.Namespace) -> TrainConfig:
    preset = MODEL_PRESETS[args.model_preset]
    new_model_name = os.getenv("NEW_MODEL_NAME", f"AgentUnity-{args.model_preset}")
    max_seq_length = args.max_seq_length or int(preset["max_seq_length"])
    return TrainConfig(
        preset_name=args.model_preset,
        model_name=os.getenv("MODEL_NAME", str(preset["model_name"])),
        new_model_name=new_model_name,
        max_seq_length=max_seq_length,
        batch_size=int(os.getenv("PER_DEVICE_BATCH_SIZE", str(preset["batch_size"]))),
        gradient_accumulation_steps=int(
            os.getenv("GRADIENT_ACCUMULATION_STEPS", str(preset["gradient_accumulation_steps"]))
        ),
        learning_rate=float(os.getenv("LEARNING_RATE", str(preset["learning_rate"]))),
        lora_r=int(os.getenv("LORA_R", str(preset["lora_r"]))),
        lora_alpha=int(os.getenv("LORA_ALPHA", str(preset["lora_alpha"]))),
        epochs=args.epochs,
        export_nvfp4=args.export_nvfp4,
        quantize_base=not args.skip_base_4bit,
    )


def load_training_dataset(dataset_path: Path) -> Dataset:
    files_index_path = dataset_path / "metadata" / "files_index.json"
    print(f"Loading dataset index from {files_index_path}...")
    raw_dataset = load_dataset("json", data_files=str(files_index_path), field="files")

    def load_content(example: dict) -> dict:
        file_path = dataset_path / example["relative_path_clean"]
        try:
            content = file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            example["text"] = ""
            return example

        example["text"] = (
            "<|im_start|>system\n"
            "You are a senior Unity and C# code assistant. Analyze code precisely and prefer maintainable implementations.\n"
            "<|im_end|>\n"
            "<|im_start|>user\n"
            f"Analyze and learn the following {example['language']} file for future coding assistance.\n"
            f"Path: {example['relative_path_clean']}\n\n"
            f"```{example['language']}\n{content}\n```\n"
            "<|im_end|>\n"
            "<|im_start|>assistant\n"
            "Understood. I have incorporated the code structure, APIs, and patterns from this file into my working context.\n"
            "<|im_end|>"
        )
        return example

    dataset = raw_dataset["train"].map(load_content)
    dataset = dataset.filter(lambda example: len(example["text"]) > 0)
    print(f"Dataset loaded with {len(dataset)} samples.")
    return dataset


def build_quantization_config(enabled: bool) -> Optional[BitsAndBytesConfig]:
    if not enabled:
        return None
    return BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )


def resolve_attention_implementation() -> str:
    if importlib.util.find_spec("flash_attn") is not None:
        return "flash_attention_2"
    else:
        return "sdpa"


def load_model_and_tokenizer(config: TrainConfig):
    quantization_config = build_quantization_config(config.quantize_base)
    attention_implementation = resolve_attention_implementation()
    print(f"Loading base model: {config.model_name}")
    model = AutoModelForCausalLM.from_pretrained(
        config.model_name,
        quantization_config=quantization_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        attn_implementation=attention_implementation,
        trust_remote_code=True,
    )
    model.config.use_cache = False

    tokenizer = AutoTokenizer.from_pretrained(config.model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    return model, tokenizer


def attach_lora(model, config: TrainConfig):
    lora_config = LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=0.05,
        target_modules=DEFAULT_TARGET_MODULES,
        bias="none",
        task_type="CAUSAL_LM",
    )

    if config.quantize_base:
        model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()
    return model, lora_config


def write_training_manifest(output_dir: Path, config: TrainConfig) -> None:
    manifest = {
        "preset": config.preset_name,
        "base_model": config.model_name,
        "new_model_name": config.new_model_name,
        "max_seq_length": config.max_seq_length,
        "batch_size": config.batch_size,
        "gradient_accumulation_steps": config.gradient_accumulation_steps,
        "learning_rate": config.learning_rate,
        "lora_r": config.lora_r,
        "lora_alpha": config.lora_alpha,
        "epochs": config.epochs,
        "export_nvfp4": config.export_nvfp4,
    }
    (output_dir / "training_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def train_adapter(dataset: Dataset, model, tokenizer, lora_config: LoraConfig, config: TrainConfig, output_dir: Path):
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=config.epochs,
        per_device_train_batch_size=config.batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        gradient_checkpointing=True,
        optim="paged_adamw_32bit",
        logging_steps=10,
        save_strategy="epoch",
        learning_rate=config.learning_rate,
        bf16=True,
        tf32=True,
        max_grad_norm=0.3,
        warmup_ratio=0.03,
        lr_scheduler_type="cosine",
        report_to="wandb" if os.getenv("WANDB_API_KEY") else "none",
        push_to_hub=True if os.getenv("HF_TOKEN") else False,
        hub_model_id=config.new_model_name,
    )

    trainer = SFTTrainer(
        model=model,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=config.max_seq_length,
        processing_class=tokenizer,
        args=training_args,
    )

    print("Starting fine-tuning...")
    trainer.train()
    print("Training complete. Saving final LoRA adapter.")
    trainer.save_model(str(output_dir))

    if os.getenv("HF_TOKEN"):
        print("Pushing adapter to Hugging Face Hub...")
        trainer.push_to_hub()


def merge_lora_adapter(base_model_name: str, adapter_dir: Path, merged_dir: Path) -> Path:
    print(f"Merging LoRA adapter into full checkpoint at {merged_dir}...")
    merged_dir.mkdir(parents=True, exist_ok=True)
    attention_implementation = resolve_attention_implementation()

    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        attn_implementation=attention_implementation,
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(model, str(adapter_dir))
    merged_model = model.merge_and_unload()
    merged_model.save_pretrained(str(merged_dir), safe_serialization=True)

    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    tokenizer.save_pretrained(str(merged_dir))
    return merged_dir


def run_command(command: list[str], cwd: Optional[Path] = None) -> None:
    print("Running command:", " ".join(command))
    subprocess.run(command, cwd=str(cwd) if cwd else None, check=True)


def quantize_merged_model_nvfp4(merged_dir: Path, compiled_dir: Path) -> None:
    modelopt_dir = Path(os.getenv("MODELOPT_DIR", "/opt/Model-Optimizer"))
    script_path = modelopt_dir / "examples" / "llm_ptq" / "scripts" / "huggingface_example.sh"
    if not script_path.exists():
        raise FileNotFoundError(
            "Model Optimizer script not found. Set MODELOPT_DIR or install NVIDIA Model Optimizer in the image."
        )

    compiled_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "bash",
        str(script_path),
        "--model",
        str(merged_dir),
        "--quant",
        "fp8",
        "--kv_cache_quant",
        "nvfp4",
        "--output_dir",
        str(compiled_dir),
    ]
    run_command(command, cwd=modelopt_dir / "examples" / "llm_ptq")


def main(args: argparse.Namespace) -> None:
    config = build_train_config(args)
    dataset_path = Path(args.dataset_path)
    model_root = Path(args.model_output_path)
    adapter_output_dir = model_root / config.new_model_name / "adapter"
    merged_output_dir = model_root / config.new_model_name / "merged"
    compiled_output_dir = model_root / config.new_model_name / "trtllm_nvfp4"

    adapter_output_dir.mkdir(parents=True, exist_ok=True)
    write_training_manifest(adapter_output_dir, config)

    dataset = load_training_dataset(dataset_path)
    model, tokenizer = load_model_and_tokenizer(config)
    model, lora_config = attach_lora(model, config)

    train_adapter(dataset, model, tokenizer, lora_config, config, adapter_output_dir)
    merged_checkpoint_dir = merge_lora_adapter(config.model_name, adapter_output_dir, merged_output_dir)

    if config.export_nvfp4:
        print("Compiling the fine-tuned merged checkpoint for Blackwell deployment with NVFP4 KV cache...")
        quantize_merged_model_nvfp4(merged_checkpoint_dir, compiled_output_dir)
        print(f"NVFP4 artifacts available at {compiled_output_dir}")

    print("Done!")


if __name__ == "__main__":
    main(parse_args())
