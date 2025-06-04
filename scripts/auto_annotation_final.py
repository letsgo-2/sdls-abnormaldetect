# scripts/auto_annotation.py

import json
from pathlib import Path
import re
import os

# Mapping of view IDs to human-readable labels
VIEW_MAP = {
    0: "top-down view",
    1: "left-down view",
    2: "front-down view",
    3: "right-down view",
    4: "left-horizontal view",
    5: "front-horizontal view",
    6: "right-horizontal view",
    7: "left-up view",
    8: "front-up view",
    9: "right-up view",
    10: "left 90° downward view",
    11: "right 90° downward view",
    12: "left 90° horizontal view",
    13: "right 90° horizontal view",
}
FILENAME_REGEX = re.compile(r"(?P<idx>\d+)_(?P<distance>near|far)_(?P<view>\d+)")


def generate_grounding(img_path: Path, anomaly_type: str, category: str, project_root: Path) -> list:
    """
    Generate grounding list from XML.
    - abnormal_types: defined with capitalized names
    - matching uses lowercase comparison
    - category field uses anomaly_type passed from desc
    """
    abnormal_types = {
        "Missing", "Inoperable Object", "Transformer Failure",
        "Unfulfilled Object", "Environmental Disturbance"
    }

    # Convert to lowercase for matching
    abnormal_types_lower = {t.lower() for t in abnormal_types}

    grounding = []
    matched = False

    label_file = Path(img_path)
    xml_path = project_root.joinpath(label_file.parent, "label", label_file.name.replace(".jpg", ".xml"))
    if not xml_path.exists():
        raise FileNotFoundError(f"[ERROR] Label XML not found: {xml_path}")

    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(xml_path)
        root = tree.getroot()

        for obj in root.findall("object"):
            name_raw = obj.findtext("name", "").strip()
            name_lower = name_raw.lower()

            bbox_node = obj.find("bndbox")
            xmin = int(bbox_node.findtext("xmin"))
            ymin = int(bbox_node.findtext("ymin"))
            xmax = int(bbox_node.findtext("xmax"))
            ymax = int(bbox_node.findtext("ymax"))
            bbox = [xmin, ymin, xmax, ymax]

            if name_lower in abnormal_types_lower:
                grounding.append({
                    "text_span": "Abnormal region",
                    "bbox": bbox,
                    "category": anomaly_type  # Use the anomaly type from the description
                })
                matched = True
            elif name_lower == "normal":
                grounding.append({
                    "text_span": "Normal region",
                    "bbox": bbox,
                    "category": "Normal"
                })
                matched = True
            else:
                grounding.append({
                    "text_span": name_raw,
                    "bbox": bbox,
                    "category": "object"
                })

        # if not matched:
            # raise ValueError(f"[ERROR] No abnormal or normal object found in XML: {xml_path}")

    except Exception as e:
        print(f"[EXCEPTION] Failed to parse XML or assign grounding for {img_path}: {e}")
        raise

    return grounding

import shutil

def collect_and_rename_images(project_root: Path, groups: dict):
    """
    收集所有图片，复制并重命名到 data/image 文件夹下，返回新旧路径映射表。
    """
    image_dir = project_root.joinpath("data", "image")
    image_dir.mkdir(parents=True, exist_ok=True)

    # 1. 收集所有图片并排序
    all_imgs = []
    for img_list in groups.values():
        all_imgs.extend(img_list)
    # 可根据需求排序（比如按照原始路径排序，保证顺序一致）
    all_imgs = sorted(set(all_imgs), key=lambda p: str(p))

    # 2. 重命名并复制
    mapping = {}
    for idx, img_path in enumerate(all_imgs, start=1):
        new_name = f"{idx:04d}.jpg"
        new_path = image_dir.joinpath(new_name)
        shutil.copyfile(img_path, new_path)
        mapping[img_path.resolve()] = new_path.relative_to(project_root)
    print(f"Copied {len(all_imgs)} images to {image_dir}")
    return mapping



def collect_image_groups_for_device(device_folder: Path) -> dict:
    """
    Traverse device_folder and group both images and txt references into
    groups keyed by (step, phase, category, idx). Also output groups to JSON for debug.
    """
    groups = {}
    # single pass: handle images and txt
    for path in device_folder.rglob("*"):
        suffix = path.suffix.lower()
        # image file
        if suffix in {'.jpg', '.jpeg', '.png'}:
            parts = path.parts
            step_seg = next((p for p in parts if p.startswith("step") and ("-pre" in p or "-post" in p)), None)
            if not step_seg:
                continue
            step, phase = step_seg.split("-", 1)
            category = parts[parts.index(step_seg) + 1]
            m = FILENAME_REGEX.match(path.stem)
            idx = int(m.group('idx')) if m else None
            key = (step, phase, category, idx)
            groups.setdefault(key, []).append(path)
        # txt file: supplement group
        elif suffix == '.txt':
            parts = path.stem.split("-")
            if len(parts) < 5:
                continue
            idx0, ref_step, ref_phase, ref_cat, ref_idx = parts[:5]
            # determine this txt's own group key
            seg = next((p for p in path.parts if p.startswith("step") and ("-pre" in p or "-post" in p)), None)
            if not seg:
                continue
            step0, phase0 = seg.split("-", 1)
            cat0 = path.parts[path.parts.index(seg) + 1]
            idx_group = int(idx0) if idx0.isdigit() else None
            key0 = (step0, phase0, cat0, idx_group)
            # resolve referenced images under same point
            point_dir = path.parent.parent.parent
            ref_folder = point_dir.joinpath(f"{ref_step}-{ref_phase}", ref_cat)
            if ref_folder.exists():
                for img in ref_folder.rglob(f"{ref_idx}_*.*"):
                    if img.suffix.lower() in {'.jpg', '.jpeg', '.png'}:
                        groups.setdefault(key0, []).append(img)
    # debug dump groups to JSON
    debug_dir = device_folder.parent.parent.joinpath("annotation")
    debug_dir.mkdir(parents=True, exist_ok=True)
    total = sum(len(v) for v in groups.values())
    # ser = {
    #     "total_count": total,
    #     "groups": {
    #         "_".join(map(str, k)) + f" ({len(v)} imgs)": [
    #             str(p.relative_to(device_folder.parent.parent)) for p in v
    #         ]
    #         for k, v in groups.items()
    #     }
    # }
    ser = {"_".join([str(x) for x in key]): [str(p.relative_to(device_folder.parent.parent)) for p in imgs]
           for key, imgs in groups.items()}
    debug_file = debug_dir.joinpath(f"groups_{device_folder.name}.json")
    debug_file.write_text(json.dumps(ser, ensure_ascii=False, indent=2), encoding='utf-8')
    return groups
    

def build_records(project_root: Path):
    meta = json.loads(project_root.joinpath("data").joinpath("metasteps_caption.json").read_text(encoding='utf-8'))
    base_folder = project_root.joinpath("data").joinpath("anomalyDataset_label")
    output_dir = project_root.joinpath("data").joinpath("annotation")
    output_dir.mkdir(parents=True, exist_ok=True)
   
    all_groups = {}
    for device_folder in base_folder.iterdir():
        if not device_folder.is_dir():
            continue
        groups = collect_image_groups_for_device(device_folder)
        for k, v in groups.items():
            all_groups.setdefault(k, []).extend(v)
    # 去重，每个分组的图片合并
    for k in all_groups:
        all_groups[k] = list(set(all_groups[k]))

    # 1. 生成图片重命名及映射
    mapping = collect_and_rename_images(project_root, all_groups)

    all_devices_records = []
    for device_folder in base_folder.iterdir():
        if not device_folder.is_dir():
            continue
        device = device_folder.name
        # collect groups once per device
        groups = collect_image_groups_for_device(device_folder)
        all_records = []
        # iterate metasteps to align descriptions by index
        for step, entry in meta.items():
            for phase in ['pre', 'post']:
                res_block = entry.get(f"{phase}CheckRes") or {}
                for category in ['normal', 'abnormal']:
                    descs = res_block.get(category) or []
                    for i, desc in enumerate(descs, start=1):
                        key = (step, phase, category, i)
                        imgs = groups.get(key) or []
                        for img in imgs:
                            m = FILENAME_REGEX.match(img.stem)
                            rec = {
                                # "Image_Id": img.relative_to(project_root).as_posix(),
                                "Image_Id": mapping[img.resolve()].as_posix(),
                                "Stage_Description": entry.get("subtask"),
                                "step": step,
                                "phase": phase,
                                "Operator": entry.get("operator"),
                                "Obj": entry.get("obj"),
                                "Start_Position": entry.get("start_position"),
                                "Dest_Position": entry.get("dest_position"),
                                "Checktype": entry.get(f"{phase}CheckType"),
                                "CheckDev": ("Realsense455" if device == "fix_arm" else "Realsense435i") + f" mounted on {device}",
                                "Detection_Location": entry.get(f"{phase}CheckLocation"),
                                "Detection_Content": entry.get(f"{phase}CheckContent"),                                
                                "Views": VIEW_MAP.get(int(m.group('view'))) if m else None,
                                "Distance": m.group('distance') if m else None,
                                "Anomaly_Label": (category == "abnormal"),
                                "Anomaly_Type": desc.get("type"),
                                "Anomaly_Label_Description": desc.get("description"),
                                "Caption": desc.get("caption"),
                                "Grounding": generate_grounding(img, desc.get("type"), category, project_root)
                            }
                            all_records.append(rec)
                            all_devices_records.append(rec)
        out = output_dir.joinpath(f"records_{device}_final.json")
        out.write_text(json.dumps(all_records, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"Wrote {len(all_records)} records to {out}")

    all_out = output_dir.joinpath("annotation.json")
    all_out.write_text(json.dumps(all_devices_records, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Wrote merged {len(all_devices_records)} records to {all_out}")

def split_by_step(project_root: Path, device: str):
    input_file = project_root.joinpath("data", "annotation", f"records_{device}.json")
    records = json.loads(input_file.read_text(encoding='utf-8'))
    by_step = {}
    for rec in records:
        by_step.setdefault(rec.get("step"), []).append(rec)
    out_dir = project_root.joinpath("data", "annotation")
    for step, recs in by_step.items():
        out_path = out_dir.joinpath(f"{device}_{step}.json")
        out_path.write_text(json.dumps(recs, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"Wrote {len(recs)} records to {out_path}")


if __name__ == "__main__":
    root = Path.cwd()
    build_records(root)
    # for dev in ["fix_arm", "mobile_arm"]:
    #     split_by_step(root, dev)
