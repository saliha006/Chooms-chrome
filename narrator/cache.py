"""Pre-generate every fixed line as a WAV clip, so the voice works offline and with no API wait (H3, D12).

    python -m narrator.cache --dry-run    # what would be generated, and how many characters (credits)
    python -m narrator.cache              # generate the missing clips into narrator/clips/<persona>/<key>.wav
    python -m narrator.cache --force      # regenerate all of them (after changing a line or a voice)

Needs ELEVENLABS_API_KEY in .env; the key is read, never printed.
"""

import argparse
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from narrator.lines import LINES

CLIPS = Path(__file__).parent / "clips"
VOICES = Path(__file__).resolve().parents[1] / "config" / "voices.yaml"


def clip_path(persona: str, key: str) -> Path:
    return CLIPS / persona / f"{key}.wav"


def todo(force: bool) -> list[tuple[str, str, str]]:
    return [(persona, key, text) for persona, lines in LINES.items() for key, text in lines.items()
            if force or not clip_path(persona, key).exists()]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="list the clips and character count, call nothing")
    ap.add_argument("--force", action="store_true", help="regenerate clips that already exist")
    args = ap.parse_args()

    voices = yaml.safe_load(VOICES.read_text())
    jobs = todo(args.force)
    print(f"{len(jobs)} clips, {sum(len(text) for _, _, text in jobs)} characters")
    if args.dry_run or not jobs:
        for persona, key, text in jobs:
            print(f"  {persona}/{key}: {text}")
        return

    load_dotenv()
    if not os.environ.get("ELEVENLABS_API_KEY"):
        sys.exit("ELEVENLABS_API_KEY not set (add it to .env)")
    from elevenlabs.client import ElevenLabs

    client = ElevenLabs(api_key=os.environ["ELEVENLABS_API_KEY"])
    for persona, key, text in jobs:
        audio = client.text_to_speech.convert(
            voice_id=voices[persona], text=text,
            model_id=voices["cached_model"], output_format=voices["cached_format"],
        )
        path = clip_path(persona, key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"".join(audio))
        print(f"  {path.relative_to(CLIPS.parent)}")


if __name__ == "__main__":
    main()
