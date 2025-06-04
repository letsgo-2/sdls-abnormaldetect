#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate six visualizations for anomaly data:
1. Dual Heatmap (Fix vs Mobile)
2. Bubble Chart (Fix size, Mobile intensity)
3. Stacked Area Chart
4. Radar Chart
5. Bubble+Color Chart (Total size, Mobile ratio)
6. Treemap (Mosaic)
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# Optional treemap library
try:
    import squarify
except ImportError:
    squarify = None


def load_df(json_path: Path) -> pd.DataFrame:
    data = json.loads(json_path.read_text(encoding='utf-8'))
    df = pd.DataFrame(data)
    df['anomaly_Type'] = df['anomaly_Type'].fillna('normal')
    df['point'] = df['image_id'].str.extract(r'/point(\d+)/')[0].astype(int)
    return df


def plot_dual_heatmap(df_fix, df_mob, types, points, out_path: Path):
    pivot_fix = df_fix.pivot_table(index='anomaly_Type', columns='point', aggfunc='size', fill_value=0)
    pivot_fix = pivot_fix.reindex(index=types, columns=points, fill_value=0)
    pivot_mob = df_mob.pivot_table(index='anomaly_Type', columns='point', aggfunc='size', fill_value=0)
    pivot_mob = pivot_mob.reindex(index=types, columns=points, fill_value=0)

    vmax = max(pivot_fix.values.max(), pivot_mob.values.max())
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    for ax, data, title in zip(axes, [pivot_fix, pivot_mob], ['Fix Arm', 'Mobile Arm']):
        im = ax.imshow(data, aspect='auto', cmap='Blues', vmin=0, vmax=vmax)
        ax.set_xticks(np.arange(len(points)))
        ax.set_xticklabels(points)
        ax.set_yticks(np.arange(len(types)))
        ax.set_yticklabels(types)
        ax.set_xlabel('Point')
        ax.set_title(title)
    axes[0].set_ylabel('Anomaly Type')
    fig.colorbar(im, ax=axes, orientation='vertical', fraction=0.02, pad=0.04, label='Count')
    plt.suptitle('Dual Heatmaps: Anomaly Type per Point')
    # plt.tight_layout(rect=[0,0.03,1,0.95])
    # 
    fig.tight_layout()
    fig.subplots_adjust(top=0.90)
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_bubble_fix_mobile(df_fix, df_mob, types, points, out_path: Path):
    pivot_fix = df_fix.pivot_table(index='anomaly_Type', columns='point', aggfunc='size', fill_value=0)
    pivot_fix = pivot_fix.reindex(index=types, columns=points, fill_value=0)
    pivot_mob = df_mob.pivot_table(index='anomaly_Type', columns='point', aggfunc='size', fill_value=0)
    pivot_mob = pivot_mob.reindex(index=types, columns=points, fill_value=0)

    X, Y = np.meshgrid(points, np.arange(len(types)))
    fix_vals = pivot_fix.values.flatten()
    mob_vals = pivot_mob.values.flatten()
    sizes = fix_vals * 20

    fig, ax = plt.subplots(figsize=(12, 6))
    sc = ax.scatter(X.flatten(), Y.flatten(), s=sizes, c=mob_vals, cmap='viridis', alpha=0.7)
    ax.set_xticks(points)
    ax.set_yticks(np.arange(len(types)))
    ax.set_yticklabels(types)
    ax.set_xlabel('Point')
    ax.set_ylabel('Anomaly Type')
    ax.set_title('Bubble Chart: Fix Size / Mobile Intensity')
    fig.colorbar(sc, label='Mobile Arm Count')
    plt.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_stacked_area(df_fix, df_mob, types, points, out_path: Path):
    pivot_fix = df_fix.pivot_table(index='anomaly_Type', columns='point', aggfunc='size', fill_value=0)
    pivot_fix = pivot_fix.reindex(index=types, columns=points, fill_value=0).T
    pivot_mob = df_mob.pivot_table(index='anomaly_Type', columns='point', aggfunc='size', fill_value=0)
    pivot_mob = pivot_mob.reindex(index=types, columns=points, fill_value=0).T

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.stackplot(points, [pivot_fix[typ] for typ in types], labels=[f'Fix {typ}' for typ in types], cmap='tab20', alpha=0.8)
    ax.stackplot(points, [pivot_mob[typ] for typ in types], labels=[f'Mobile {typ}' for typ in types], cmap='tab20', alpha=0.4)
    ax.set_xticks(points)
    ax.set_xlabel('Point')
    ax.set_ylabel('Count')
    ax.set_title('Stacked Area: Anomaly Type per Point')
    ax.legend(loc='upper left', ncol=2, fontsize=8)
    plt.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_radar(df_fix, df_mob, types, out_path: Path):
    fix_counts = df_fix['anomaly_Type'].value_counts().reindex(types, fill_value=0).values
    mob_counts = df_mob['anomaly_Type'].value_counts().reindex(types, fill_value=0).values
    angles = np.linspace(0, 2*np.pi, len(types), endpoint=False).tolist()
    angles += angles[:1]
    fix_plot = np.concatenate((fix_counts, [fix_counts[0]]))
    mob_plot = np.concatenate((mob_counts, [mob_counts[0]]))

    fig = plt.figure(figsize=(8, 6))
    ax = fig.add_subplot(111, polar=True)
    ax.plot(angles, fix_plot, color='b', linewidth=2, label='Fix Arm')
    ax.fill(angles, fix_plot, color='b', alpha=0.25)
    ax.plot(angles, mob_plot, color='r', linewidth=2, label='Mobile Arm')
    ax.fill(angles, mob_plot, color='r', alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(types, fontsize=9)
    ax.set_title('Radar Chart: Anomaly Type Distribution')
    ax.legend(loc='upper right', bbox_to_anchor=(1.3,1.1))
    plt.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_bubble_color(df_fix, df_mob, types, points, out_path: Path):
    pivot_fix = df_fix.pivot_table(index='point', columns='anomaly_Type', aggfunc='size', fill_value=0)
    pivot_fix = pivot_fix.reindex(columns=types, index=points, fill_value=0)
    pivot_mob = df_mob.pivot_table(index='point', columns='anomaly_Type', aggfunc='size', fill_value=0)
    pivot_mob = pivot_mob.reindex(columns=types, index=points, fill_value=0)

    X, Y = np.meshgrid(points, np.arange(len(types)))
    fix_vals = pivot_fix.values.T.flatten()
    mob_vals = pivot_mob.values.T.flatten()
    total_vals = fix_vals + mob_vals
    ratio = np.divide(mob_vals, total_vals, out=np.zeros_like(mob_vals, float), where=total_vals>0)

    fig, ax = plt.subplots(figsize=(12, 6))
    sc = ax.scatter(X.flatten(), Y.flatten(), s=total_vals*20, c=ratio, cmap='coolwarm', alpha=0.7)
    ax.set_xticks(points)
    ax.set_yticks(np.arange(len(types)))
    ax.set_yticklabels(types)
    ax.set_xlabel('Point')
    ax.set_ylabel('Anomaly Type')
    ax.set_title('Bubble+Color: Total Size & Mobile Ratio')
    fig.colorbar(sc, label='Mobile / Total')
    plt.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_treemap(df_fix, df_mob, types, out_path: Path):
    if squarify is None:
        print('squarify not available; skipping treemap')
        return
    fix_counts = df_fix['anomaly_Type'].value_counts().reindex(types, fill_value=0).values
    mob_counts = df_mob['anomaly_Type'].value_counts().reindex(types, fill_value=0).values
    labels, sizes, colors = [], [], []
    base_colors = plt.cm.Set3(np.linspace(0,1,len(types)))
    for i, t in enumerate(types):
        f, m = fix_counts[i], mob_counts[i]
        if f>0:
            labels.append(f'Fix {t}\n{f}')
            sizes.append(f)
            colors.append(base_colors[i])
        if m>0:
            labels.append(f'Mobile {t}\n{m}')
            sizes.append(m)
            colors.append(base_colors[i]*0.7)
    fig = plt.figure(figsize=(10, 6))
    squarify.plot(sizes=sizes, label=labels, color=colors, alpha=0.8, text_kwargs={'fontsize':8})
    plt.axis('off')
    plt.title('Treemap: Anomaly Type by Arm')
    plt.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def main():
    root = Path(__file__).parent.parent
    ann = root.joinpath('data', 'annotation')
    plot = root.joinpath('data', 'plot')
    plot.mkdir(parents=True, exist_ok=True)

    df_fix = load_df(ann.joinpath('records_fix_arm.json'))
    df_mob = load_df(ann.joinpath('records_mobile_arm.json'))
    types = sorted(df_fix['anomaly_Type'].unique())
    points = list(range(1,12))

    plot_dual_heatmap(df_fix, df_mob, types, points, plot.joinpath('dual_heatmap.png'))
    plot_bubble_fix_mobile(df_fix, df_mob, types, points, plot.joinpath('bubble_fix_mobile.png'))
    plot_stacked_area(df_fix, df_mob, types, points, plot.joinpath('stacked_area.png'))
    plot_radar(df_fix, df_mob, types, plot.joinpath('radar_chart.png'))
    plot_bubble_color(df_fix, df_mob, types, points, plot.joinpath('bubble_color.png'))
    plot_treemap(df_fix, df_mob, types, plot.joinpath('treemap.png'))

if __name__=='__main__':
    main()
