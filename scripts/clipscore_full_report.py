import json
import pandas as pd
from pathlib import Path

# 定义视角列表（索引0~13）
VIEWS_ORDER = [
    "top-down view", "left-down view", "front-down view", "right-down view",
    "left-horizontal view", "front-horizontal view", "right-horizontal view",
    "left-up view", "front-up view", "right-up view",
    "left 90° downward view", "right 90° downward view",
    "left 90° horizontal view", "right 90° horizontal view",
]

# 路径设置
BASE_DIR = Path(__file__).parent.parent
FIX_PATH = BASE_DIR.joinpath("data", "clipscores", "fix_clipscoreslow_results.json")
MOBILE_PATH = BASE_DIR.joinpath("data", "clipscores", "mobile_clipscoreslow_results.json")
OUTPUT_DIR = BASE_DIR.joinpath("data", "clipscores", "reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 加载 JSON 文件
def load_json(path):
    if not path.exists():
        print(f"⚠️ 文件未找到: {path}")
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)

# 解析 clip_score、near/far 和视角 index
def parse_data(data):
    records = []
    for item in data:
        image_id = item.get("image_id", "")
        score = item.get("clip_score", None)
        parts = Path(image_id).stem.split("_")
        if len(parts) == 3 and score is not None:
            distance = parts[1]  # near / far
            view_index = int(parts[2])
            records.append({
                "distance": distance,
                "view": view_index,
                "clip_score": score
            })
    return pd.DataFrame(records)

def main():
    # 加载数据
    fix_data = load_json(FIX_PATH)
    mobile_data = load_json(MOBILE_PATH)
    all_data = fix_data + mobile_data

    df = parse_data(all_data)

    if df.empty:
        print("❌ 没有有效数据，请检查 JSON 文件内容。")
        return

    # 平均值表
    pivot_mean = df.pivot_table(
        index="distance", columns="view", values="clip_score",
        aggfunc="mean", margins=True, margins_name="Average"
    )
    pivot_mean.to_csv(OUTPUT_DIR.joinpath("clipscore_avg.csv"))

    # 累计值表
    pivot_sum = df.pivot_table(
        index="distance", columns="view", values="clip_score",
        aggfunc="sum", margins=True, margins_name="Total"
    )
    pivot_sum.to_csv(OUTPUT_DIR.joinpath("clipscore_sum.csv"))

    # 计数字段
    pivot_count = df.pivot_table(
        index="distance", columns="view", values="clip_score",
        aggfunc="count", margins=True, margins_name="Total"
    )
    pivot_count.to_csv(OUTPUT_DIR.joinpath("clipscore_count.csv"))

    print("✅ CLIPScore 分析完成，文件保存在:", OUTPUT_DIR)

if __name__ == "__main__":
    main()
