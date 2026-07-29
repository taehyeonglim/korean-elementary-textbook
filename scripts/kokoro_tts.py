#!/usr/bin/env python3
"""Synthesize a pinned Kokoro-82M job to a 24 kHz PCM WAV file.

This helper intentionally owns only local inference. ``generate-audio.mjs``
owns plan validation, MP3 encoding, transcript/metadata generation, and the
transactional promotion into ``public/`` and ``content/``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np
import soundfile as sf
from huggingface_hub import hf_hub_download
from kokoro import KModel, KPipeline

MODEL_REPOSITORY = "hexgrad/Kokoro-82M"
MODEL_REVISION = "f3ff3571791e39611d31c381e3a41a3af07b4987"
MODEL_WEIGHTS = "kokoro-v1_0.pth"
MODEL_CONFIG = "config.json"
SAMPLE_RATE = 24000
SEGMENT_SILENCE_SECONDS = 0.45


def fail(message: str) -> None:
    raise ValueError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(filename: str) -> Path:
    """Fetch an exact repository revision; no mutable ``main`` fallback."""
    return Path(
        hf_hub_download(
            repo_id=MODEL_REPOSITORY,
            filename=filename,
            revision=MODEL_REVISION,
        )
    )


def read_job(path: Path) -> dict[str, Any]:
    try:
        job = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        fail(f"Cannot read Kokoro job {path}: {error}")
    if not isinstance(job, dict) or not isinstance(job.get("segments"), list) or not job["segments"]:
        fail("Kokoro job requires a non-empty segments array")
    return job


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Validated JSON job from generate-audio.mjs")
    parser.add_argument("--output", required=True, type=Path, help="Temporary PCM WAV output")
    parser.add_argument("--provenance", required=True, type=Path, help="Temporary JSON provenance output")
    args = parser.parse_args()

    # Keep this deterministic on Apple Silicon and Linux CI. MPS can be opted
    # into later only after a byte/duration reproducibility policy is defined.
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    job = read_job(args.input)
    expected = {
        "backend": "kokoro",
        "model": MODEL_REPOSITORY,
        "modelRevision": MODEL_REVISION,
    }
    for key, value in expected.items():
        if job.get(key) != value:
            fail(f"Kokoro job {key} must be {value}")

    config_path = download(MODEL_CONFIG)
    weights_path = download(MODEL_WEIGHTS)
    model = KModel(config=str(config_path), model=str(weights_path)).to("cpu").eval()
    pipeline = KPipeline(lang_code="a", model=model, device="cpu")
    silence = np.zeros(round(SAMPLE_RATE * SEGMENT_SILENCE_SECONDS), dtype=np.float32)
    pieces: list[np.ndarray] = []
    voice_artifacts: dict[str, dict[str, str]] = {}

    for index, segment in enumerate(job["segments"]):
        if not isinstance(segment, dict):
            fail(f"segments[{index}] must be an object")
        role = segment.get("role")
        text = segment.get("text")
        voice = segment.get("voice")
        if not all(isinstance(value, str) and value.strip() for value in (role, text, voice)):
            fail(f"segments[{index}] requires non-empty role, text, and voice")
        voice_path = download(f"voices/{voice}.pt")
        voice_artifacts.setdefault(voice, {"path": f"voices/{voice}.pt", "sha256": sha256(voice_path)})
        audio_parts = [result.output.audio.numpy() for result in pipeline(text, voice=str(voice_path), speed=1.0)]
        if not audio_parts:
            fail(f"segments[{index}] produced no audio")
        pieces.append(np.concatenate(audio_parts).astype(np.float32, copy=False))
        if index < len(job["segments"]) - 1:
            pieces.append(silence)

    wav = np.concatenate(pieces)
    if wav.size == 0 or not np.isfinite(wav).all():
        fail("Kokoro produced invalid PCM samples")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, wav, SAMPLE_RATE, subtype="PCM_16")
    provenance = {
        "backend": "kokoro",
        "model": MODEL_REPOSITORY,
        "modelRevision": MODEL_REVISION,
        "modelArtifacts": {
            "config": {"path": MODEL_CONFIG, "sha256": sha256(config_path)},
            "weights": {"path": MODEL_WEIGHTS, "sha256": sha256(weights_path)},
        },
        "voiceArtifacts": voice_artifacts,
        "sampleRate": SAMPLE_RATE,
        "frames": int(wav.size),
        "durationSeconds": round(wav.size / SAMPLE_RATE, 3),
        "pcmSha256": sha256(args.output),
    }
    args.provenance.parent.mkdir(parents=True, exist_ok=True)
    args.provenance.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "durationSeconds": provenance["durationSeconds"]}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # Keep Node's release gate error focused.
        print(f"Kokoro synthesis failed: {error}", file=sys.stderr)
        raise SystemExit(1)
