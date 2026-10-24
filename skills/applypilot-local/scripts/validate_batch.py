"""Agent helper: check a staging folder or integrity of a published batch."""

import argparse
import json
from pathlib import Path

from batch_lib import (
    BASE_GENERATED_FILES,
    GENERATED_FILES,
    read_json,
    require,
    safe_file,
    sha256,
    validate,
)


def check(root):
    root = Path(root)
    batch, summary, _ = validate(root)
    manifest_path = root / "manifest.json"
    if manifest_path.exists():
        manifest = read_json(manifest_path)
        require(
            manifest["run_id"] == batch["run_id"], "Manifest run ID disagrees with batch input."
        )
        require(manifest["summary"] == summary, "Manifest counts disagree with actual materials.")
        hashes = manifest.get("file_hashes", {})
        actual = {
            file.relative_to(root).as_posix()
            for file in root.rglob("*")
            if file.is_file() and file != manifest_path
        }
        require(set(hashes) == actual, "Published file inventory changed.")
        required = GENERATED_FILES if manifest["schema_version"] == 2 else BASE_GENERATED_FILES
        require(required - {"manifest.json"} <= actual, "Published indexes are missing.")
        for relative, expected in hashes.items():
            require(
                sha256(safe_file(root, relative)) == expected, f"Published file changed: {relative}"
            )
    return {"run_id": batch["run_id"], "summary": summary, "published": manifest_path.exists()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(check(args.folder)))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"Batch validation failed: {exc}\n")


if __name__ == "__main__":
    main()
