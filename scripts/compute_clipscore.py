#!/usr/bin/env python3
import json
import argparse
from pathlib import Path
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
from tqdm import tqdm
from scipy.stats import hmean
import numpy as np

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"找不到 JSON 文件：{path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"JSON 文件为空：{path}")
    return json.loads(text)

def compute_scores(
    records: list,
    images_root: Path,
    references: dict = None,
    device: str = "cuda",
    prefix: str = "A photo depicts",
    weight: float = 2.5,
):
    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
    proc  = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    clip_scores = {}
    ref_scores  = {}

    for rec in tqdm(records, desc="Evaluating"):
        rel_img = Path(rec["image_id"])
        img_path = images_root.joinpath(rel_img).resolve()
        # 打印每张图片的绝对路径
        # print(f"→ Image ID: {rel_img}  → Resolved Path: {img_path}")

        if not img_path.exists():
            clip_scores[str(rel_img)] = None
            ref_scores[str(rel_img)]  = None
            continue

        img = Image.open(img_path).convert("RGB")
        cand_desc = rec.get("Anomaly Label Description", "").strip()
        text_c = f"{prefix} {cand_desc}"
        inputs = proc(text=[text_c], images=[img], return_tensors="pt", padding=True).to(device)

        with torch.no_grad():
            v = model.get_image_features(**{k: v for k, v in inputs.items() if k.startswith("pixel")})
            c = model.get_text_features(**{k: v for k, v in inputs.items() if k.startswith("input")})
        v = v / v.norm(p=2, dim=-1, keepdim=True)
        c = c / c.norm(p=2, dim=-1, keepdim=True)

        cos_ci = (v * c).sum().item()
        s_ci = weight * max(cos_ci, 0.0)
        clip_scores[str(rel_img)] = s_ci        

        # 打印得分
        # print(f"   clip_score: {clip_scores[str(rel_img)]:.4f}")
        # RefCLIPScore 部分（若有提供 references_json）
        # if references and str(rel_img) in references:
        #     ref_sims = []
        #     for ref in references[str(rel_img)]:
        #         inp = proc(text=[f"{prefix} {ref}"], images=[img], return_tensors="pt", padding=True).to(device)
        #         with torch.no_grad():
        #             rv = model.get_image_features(**{k: v for k, v in inp.items() if k.startswith("pixel")})
        #             rc = model.get_text_features(**{k: v for k, v in inp.items() if k.startswith("input")})
        #         rv = rv / rv.norm(p=2, dim=-1, keepdim=True)
        #         rc = rc / rc.norm(p=2, dim=-1, keepdim=True)
        #         sim = max((rv * rc).sum().item(), 0.0)
        #         ref_sims.append(weight * sim)
        #     ref_scores[str(rel_img)] = sum(ref_sims) / len(ref_sims) if ref_sims else None
        #     print(f"   ref_score: {ref_scores[str(rel_img)]:.4f}")
        # else:
        #     ref_scores[str(rel_img)] = None
        ref_text = rec.get("caption", "").strip()
        if ref_text:
            # 用 CLIPProcessor 对文本各自 token 再提取特征
            inp_ref = proc(text=[text_c, f"{prefix} {ref_text}"], images=None,
                           return_tensors="pt", padding=True).to(device)
            # Processor 返回 'input_ids' 和 'attention_mask'
            t_feats = model.get_text_features(**{k:v for k,v in inp_ref.items() if k.startswith("input")})
            # t_feats[0] 对应候选描述，t_feats[1] 对应参考描述
            t_c, t_r = t_feats[0:1], t_feats[1:2]
            t_c = t_c / t_c.norm(p=2, dim=-1, keepdim=True)
            t_r = t_r / t_r.norm(p=2, dim=-1, keepdim=True)
            cos_cr = (t_c * t_r).sum().item()
            s_cr =  max(cos_cr, 0.0)

            # 3. 按论文定义取二者的谐波平均
            #    RefCLIPScore = HMean(s_ci, s_cr)
            ref_scores[str(rel_img)] = float(hmean([s_ci, s_cr]))
        else:
            ref_scores[str(rel_img)] = None




    return clip_scores, ref_scores

def main():
    parser = argparse.ArgumentParser(description="Compute CLIPScore (+ optional RefCLIPScore)")
    parser.add_argument(
        "records_json",
        type=Path,
        help="records JSON 文件相对路径，如 data/annotation/records_fix_arm.json"
    )
    parser.add_argument(
        "--references_json",
        type=Path,
        default=None,
        help="可选的参考描述 JSON 文件相对路径"
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent.resolve()
    # 打印项目根目录
    # print(f"Project root: {project_root}")

    # 拼接并打印 JSON 路径
    records_path = project_root.joinpath(args.records_json).resolve()
    # print(f"Records JSON path: {records_path}")

    references_path = None
    if args.references_json:
        references_path = project_root.joinpath(args.references_json).resolve()
        print(f"References JSON path: {references_path}")

    # images_root = project_root.joinpath("data", "anomalyDataset").resolve()
    images_root = project_root
    # print(f"Images root directory: {images_root}")

    records    = load_json(records_path)
    references = load_json(references_path) if references_path else None

    device = "cuda" if torch.cuda.is_available() else "cpu"
    clip_scores, ref_scores = compute_scores(
        records, images_root, references, device=device
    )

    out = []
    for rec in records:
        rel_img  = rec["image_id"]
        abs_path = images_root.joinpath(rel_img).resolve()
        out.append({
            "image_id":      rel_img,
            "absolute_path": str(abs_path),
            "clip_score":    clip_scores.get(rel_img),
            "ref_clip_score":ref_scores.get(rel_img),  # 输出键名改为 ref_clip_score
            "description":   rec.get("Anomaly Label Description", ""),
            "caption":       rec.get("caption", "")
        })

    out_path = project_root.joinpath("clipscore_results.json").resolve()
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"完成：处理 {len(records)} 条记录，结果保存在 {out_path}")

if __name__ == "__main__":
    main()
