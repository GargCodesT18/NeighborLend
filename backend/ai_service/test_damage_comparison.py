"""Compare before/after item photos using Gemini's multimodal API.

This is a standalone experiment; it does not modify or connect to application
workflows, records, or the database.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from google import genai
from google.genai import types
from PIL import Image
from pydantic import BaseModel, Field, ValidationError


MODEL_ID = "gemini-3.8-flash"
BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
MAX_COMBINED_IMAGE_BYTES = 18 * 1024 * 1024


class DamageFinding(BaseModel):
    damage_type: Literal["scratch", "crack", "dent", "broken_part", "missing_part", "other"]
    location: str = Field(description="Where the damage appears on the item, or 'unclear'.")
    description: str
    severity: Literal["none", "minor", "moderate", "severe", "uncertain"]
    confidence: float = Field(ge=0, le=1, description="Visual assessment confidence from 0 to 1.")


class DamageComparison(BaseModel):
    overall_result: Literal[
        "no_potential_new_damage",
        "potential_new_damage",
        "uncertain",
    ]
    comparison_quality: Literal["good", "limited", "poor"]
    summary: str
    pre_existing_damage: list[DamageFinding]
    potential_new_damage: list[DamageFinding]
    uncertain_findings: list[DamageFinding]
    limitations: list[str]


def load_api_key() -> str | None:
    """Use an exported key first, then backend/.env, then the project .env."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key

    for env_path in (BACKEND_DIR / ".env", PROJECT_DIR / ".env"):
        if env_path.is_file():
            key = str(dotenv_values(env_path).get("GEMINI_API_KEY", "") or "").strip()
            if key:
                return key
    return None


def load_image(path: Path) -> tuple[bytes, str]:
    """Validate an image and return API-supported bytes plus its MIME type."""
    if not path.is_file():
        raise ValueError(f"Image file does not exist: {path}")

    try:
        with Image.open(path) as image:
            image.load()
            image_format = (image.format or "").upper()
            if image.width < 1 or image.height < 1:
                raise ValueError("Image has no visible pixels.")

            mime_type = {
                "JPEG": "image/jpeg",
                "PNG": "image/png",
                "WEBP": "image/webp",
            }.get(image_format)

            if mime_type:
                data = path.read_bytes()
            else:
                converted = image.convert("RGB")
                from io import BytesIO

                buffer = BytesIO()
                converted.save(buffer, format="JPEG", quality=92)
                data = buffer.getvalue()
                mime_type = "image/jpeg"
    except (OSError, Image.DecompressionBombError) as exc:
        raise ValueError(f"Could not read a valid image from {path}: {exc}") from exc

    return data, mime_type


def build_prompt() -> str:
    return """Compare the same borrowed item in these two labeled photos.

The BEFORE image was taken before borrowing. The AFTER image was taken after
return. Identify only visible signs of scratches, cracks, dents, broken parts,
or missing parts. For every finding, assign exactly one category:

- pre_existing_damage: clearly visible in BEFORE, whether or not it remains visible in AFTER.
- potential_new_damage: clearly visible in AFTER and not visible in BEFORE.
- uncertain_findings: visibility, occlusion, lighting, resolution, or framing prevents a reliable decision.

Do not call damage new just because a different camera angle, crop, lighting,
blur, or obstruction reveals a surface that cannot be compared in BEFORE. Do
not infer damage from shadows or reflections. If the photos may show different
items, say so in limitations and use an uncertain overall result. Assess
comparison_quality as poor when the item or relevant surfaces cannot be
matched, limited when only some surfaces can be compared, and good when useful
surfaces align clearly. A finding's confidence is a visual estimate from 0 to
1, not a probability or proof.

Set overall_result to potential_new_damage only when at least one finding is
clearly a potential new issue; use no_potential_new_damage when the comparable
surfaces show no potential new damage; otherwise use uncertain. Return only
the requested JSON object, following the provided schema. Use empty arrays
when a finding category has no visible findings. If an image is unclear, state
that in limitations and do not overstate certainty."""


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def error_payload(error_type: str, message: str, before: Path, after: Path) -> dict:
    return {
        "status": "error",
        "model": MODEL_ID,
        "images": {"before": before.name, "after": after.name},
        "error": {"type": error_type, "message": message},
    }


def compare_images(before_path: Path, after_path: Path, output_path: Path) -> int:
    before_path = before_path.expanduser().resolve()
    after_path = after_path.expanduser().resolve()
    output_path = output_path.expanduser().resolve()

    try:
        before_bytes, before_mime = load_image(before_path)
        after_bytes, after_mime = load_image(after_path)
    except ValueError as exc:
        save_json(output_path, error_payload("invalid_image", str(exc), before_path, after_path))
        print(f"Image error: {exc}\nResult saved to {output_path}", file=sys.stderr)
        return 2

    if len(before_bytes) + len(after_bytes) > MAX_COMBINED_IMAGE_BYTES:
        message = "The two encoded images exceed the 18 MiB combined inline request limit. Resize or recompress them first."
        save_json(output_path, error_payload("images_too_large", message, before_path, after_path))
        print(f"Image error: {message}\nResult saved to {output_path}", file=sys.stderr)
        return 2

    api_key = load_api_key()
    if not api_key:
        message = "GEMINI_API_KEY was not found in the environment, backend/.env, or project-root .env."
        save_json(output_path, error_payload("missing_api_key", message, before_path, after_path))
        print(f"Configuration error: {message}\nResult saved to {output_path}", file=sys.stderr)
        return 2

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[
                build_prompt(),
                "BEFORE borrowing:",
                types.Part.from_bytes(data=before_bytes, mime_type=before_mime),
                "AFTER returning:",
                types.Part.from_bytes(data=after_bytes, mime_type=after_mime),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DamageComparison,
            ),
        )
    except Exception as exc:  # SDK/API exceptions vary by transport and status.
        message = str(exc).replace(api_key, "[REDACTED]")[:1200]
        save_json(
            output_path,
            error_payload("gemini_api_error", f"{type(exc).__name__}: {message}", before_path, after_path),
        )
        print(f"Gemini request failed: {type(exc).__name__}: {message}\nResult saved to {output_path}", file=sys.stderr)
        return 1

    try:
        response_text = response.text or ""
    except Exception as exc:
        message = f"Could not read Gemini's response text: {type(exc).__name__}: {exc}"
        message = message.replace(api_key, "[REDACTED]")[:1200]
        save_json(output_path, error_payload("invalid_response", message, before_path, after_path))
        print(f"Invalid model response: {message}\nResult saved to {output_path}", file=sys.stderr)
        return 1

    if not isinstance(response_text, str):
        response_text = str(response_text)
    if not response_text.strip():
        message = "Gemini returned no text content."
        save_json(output_path, error_payload("invalid_response", message, before_path, after_path))
        print(f"Invalid model response: {message}\nResult saved to {output_path}", file=sys.stderr)
        return 1

    try:
        comparison = DamageComparison.model_validate_json(response_text)
    except (ValidationError, ValueError, json.JSONDecodeError) as exc:
        message = f"Gemini response did not match the required JSON schema: {exc}"
        payload = error_payload("invalid_response", message, before_path, after_path)
        payload["response_excerpt"] = response_text[:2000]
        save_json(output_path, payload)
        print(f"Invalid model response: {message}\nResult saved to {output_path}", file=sys.stderr)
        return 1

    payload = {
        "status": "ok",
        "model": MODEL_ID,
        "images": {"before": before_path.name, "after": after_path.name},
        "comparison": comparison.model_dump(mode="json"),
    }
    save_json(output_path, payload)
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"\nResult saved to {output_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare before/after item photos with Gemini and save structured JSON."
    )
    parser.add_argument("before", type=Path, help="Photo taken BEFORE borrowing")
    parser.add_argument("after", type=Path, help="Photo taken AFTER returning")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("damage_comparison_result.json"),
        help="Output JSON path (default: damage_comparison_result.json)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(compare_images(args.before, args.after, args.output))
