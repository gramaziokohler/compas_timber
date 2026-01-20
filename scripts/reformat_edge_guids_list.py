import json
import shutil
from pathlib import Path
from typing import Any

SRC = Path("../data/model_test.json")
BACKUP = SRC.with_suffix(".json.bak")


def transform_dict(d: dict) -> None:
    # element_a_guid + element_b_guid -> element_guids (preserve order element_a, element_b)
    if "element_a_guid" in d and "element_b_guid" in d:
        d["element_guids"] = [d["element_a_guid"], d["element_b_guid"]]
        del d["element_a_guid"]
        del d["element_b_guid"]

    # cross_beam_guid + main_beam_guid -> element_guids (preserve order cross_beam, main_beam)
    if "cross_beam_guid" in d and "main_beam_guid" in d:
        d["element_guids"] = [d["main_beam_guid"], d["cross_beam_guid"]]
        del d["cross_beam_guid"]
        del d["main_beam_guid"]


def walk(obj: Any) -> Any:
    if isinstance(obj, dict):
        # transform this dict first (so nested structures inside replaced keys are still walked)
        transform_dict(obj)
        for k, v in list(obj.items()):
            obj[k] = walk(v)
        return obj
    if isinstance(obj, list):
        return [walk(i) for i in obj]
    return obj


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Source file not found: {SRC}")

    # backup original
    shutil.copy2(SRC, BACKUP)

    with SRC.open("r", encoding="utf-8") as f:
        data = json.load(f)

    data = walk(data)

    with SRC.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()
