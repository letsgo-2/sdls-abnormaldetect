#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate three plots:
1. Radar chart: Combined Abnormal vs Normal counts per view
2. Radar chart: Distribution of 5 Anomaly Types across 14 views
3. Bubble+Color Chart: Total abnormal count & mobile ratio by Point and Type
"""
import json,re
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import pandas as pd

# Consistent view order (14 possible views)
VIEWS_ORDER = [
    "top-down view",
    "left-down view",
    "front-down view",
    "right-down view",
    "left-horizontal view",
    "front-horizontal view",
    "right-horizontal view",
    "left-up view",
    "front-up view",
    "right-up view",
    "left 90° downward view",
    "right 90° downward view",
    "left 90° horizontal view",
    "right 90° horizontal view",
]
ALL_VIEWS = [
    "top-down view", "left-down view", "front-down view", "right-down view","left 90° downward view", "right 90° downward view",
    "left-horizontal view", "front-horizontal view", "right-horizontal view","left 90° horizontal view", "right 90° horizontal view",
    "left-up view", "front-up view", "right-up view"     
]  # for heatmaps, same grouping: down->horizontal->up
def load_records(fix_path: Path, mob_path: Path):
    """Load fix and mobile records and return combined lists."""
    fix = json.loads(fix_path.read_text(encoding='utf-8'))
    mob = json.loads(mob_path.read_text(encoding='utf-8'))
    return fix, mob


def plot_combined_radar(fix, mob, out_path: Path):
    """Radar: combined abnormal vs normal counts per view"""
    records = fix + mob
    # views = sorted({r['views'] for r in records})
    views = [v for v in VIEWS_ORDER if any(r['views']==v for r in records)]
    # Count
    abn = {v:0 for v in views}
    norm = {v:0 for v in views}
    for r in records:
        if r.get('anomaly_Label'):
            abn[r['views']] += 1
        else:
            norm[r['views']] += 1
    # Prepare
    labels = views
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]
    abn_vals = [abn[v] for v in labels] + [abn[labels[0]]]
    norm_vals = [norm[v] for v in labels] + [norm[labels[0]]]
    # Plot
    fig, ax = plt.subplots(subplot_kw=dict(polar=True), figsize=(8,6))
    ax.plot(angles, abn_vals, color='r', linewidth=2, label='Abnormal')
    ax.fill(angles, abn_vals, color='r', alpha=0.25)
    ax.plot(angles, norm_vals, color='g', linewidth=2, label='Normal')
    ax.fill(angles, norm_vals, color='g', alpha=0.25)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=8)
    ax.set_title('Combined Abnormal vs Normal Counts per View', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3,1.1))
    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_anomaly_types_radar(fix, mob, out_path: Path):
    """Radar: 5 anomaly types across 14 views"""
    records = fix + mob
    # Define ordered 14 views
    # views = [
    #     "top-down view","left-down view","front-down view","right-down view",
    #     "left-horizontal view","front-horizontal view","right-horizontal view",
    #     "left-up view","front-up view","right-up view",
    #     "left 90° downward view","right 90° downward view",
    #     "left 90° horizontal view","right 90° horizontal view"
    # ]
    views = [v for v in VIEWS_ORDER if any(r['views']==v for r in records)]
    # anomaly types
    types = sorted({r['anomaly_Type'] for r in records if r.get('anomaly_Label')})
    # Count per view per type
    counts = {t:[0]*len(views) for t in types}
    for r in records:
        if r.get('anomaly_Label'):
            v = r['views']
            t = r['anomaly_Type']
            if v in views and t in counts:
                counts[t][views.index(v)] += 1
    #compute total per view
    # total = [sum(counts[t][i] for t in types) for i in range(len(views))]
    # Radar prep
    angles = np.linspace(0, 2*np.pi, len(views), endpoint=False).tolist()
    angles += angles[:1]
# 
    # total_vals = total + [total[0]]

    fig, ax = plt.subplots(subplot_kw=dict(polar=True), figsize=(8,6))
    cmap = plt.get_cmap('tab10')
    for i,t in enumerate(types):
        vals = counts[t] + [counts[t][0]]
        color = cmap(i)
        ax.plot(angles, vals, color=color, linewidth=2, label=t)
        ax.fill(angles, vals, color=color, alpha=0.25)
    
    # plot total
    # ax.plot(angles, total_vals, color='k', linewidth=2, linestyle='--', label='Total')
    # ax.fill(angles, total_vals, color='k', alpha=0.1)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(views, fontsize=7)
    ax.set_title('Distribution of Anomaly Types Across Views', pad=20)
    ax.legend(loc='upper right', bbox_to_anchor=(1.3,1.1), fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)


def plot_bubble_color(fix, mob, out_path: Path):
    """Bubble+Color: total abnormal count & mobile ratio by point and anomaly type"""
    # points and types
    import re
    pts = list(range(1,12))
    types = sorted({r['anomaly_Type'] for r in fix+mob if r.get('anomaly_Label')})
    # Matrices
    fix_counts = {t:{p:0 for p in pts} for t in types}
    mob_counts = {t:{p:0 for p in pts} for t in types}
    for r in fix:
        if r.get('anomaly_Label'):
            m = re.search(r'/point(\d+)/', r['image_id'])
            if m: fix_counts[r['anomaly_Type']][int(m.group(1))]+=1
    for r in mob:
        if r.get('anomaly_Label'):
            m = re.search(r'/point(\d+)/', r['image_id'])
            if m: mob_counts[r['anomaly_Type']][int(m.group(1))]+=1
    # Flatten
    X,Y = np.meshgrid(pts, range(len(types)))
    fvals = np.array([fix_counts[t][p] for t in types for p in pts])
    mvals = np.array([mob_counts[t][p] for t in types for p in pts])
    total = fvals + mvals
    ratio = np.divide(mvals, total, out=np.zeros_like(mvals,float), where=total>0)
    # Plot
    fig, ax = plt.subplots(figsize=(12,6))
    sc = ax.scatter(X.flatten(), Y.flatten(), s=total*20, c=ratio, cmap='coolwarm', alpha=0.7)
    ax.set_xticks(pts)
    ax.set_xticklabels([f'Point {p}' for p in pts], rotation=45)
    ax.set_yticks(range(len(types)))
    ax.set_yticklabels(types)
    ax.set_xlabel('Point')
    ax.set_ylabel('Anomaly Type')
    ax.set_title('Total Abnormal Count & Mobile Ratio by Point and Type')
    fig.colorbar(sc, label='Mobile / Total')
    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)

def plot_heatmap_ordered(fix, mob, out_path: Path):
    # Heatmap: Abnormal count by view and point, with grouped order down->horizontal->up
    records = fix + mob
    abn = [r for r in records if r.get('anomaly_Label')]
    views = [v for v in ALL_VIEWS if any(r['views'] == v for r in abn)]
    pts = list(range(1, 12))
    data = []
    for r in abn:
        m = re.search(r'/point(\d+)/', r['image_id'])
        if m:
            data.append((r['views'], int(m.group(1))))
    df = pd.DataFrame(data, columns=['view', 'point'])
    pivot = df.pivot_table(index='view', columns='point', aggfunc='size', fill_value=0)
    pivot = pivot.reindex(index=views, columns=pts, fill_value=0)
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(pivot, aspect='auto', cmap='Blues')
    ax.set_xticks(np.arange(len(pts)))
    ax.set_xticklabels(pts)
    ax.set_yticks(np.arange(len(views)))
    ax.set_yticklabels(views)
    ax.set_xlabel('Point')
    ax.set_ylabel('View')
    ax.set_title('Heatmap: Abnormal Count by View and Point (Grouped Order)', pad=20)
    ax.grid(True, linestyle='--')
    fig.colorbar(im, ax=ax, label='Abnormal Count', fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
def plot_heatmap_split(fix, mob, out_path_fix: Path, out_path_mob: Path):
    """Generate two heatmaps: one for Fix Arm, one for Mobile Arm"""
    for records, label, path in [(fix, 'Fix Arm', out_path_fix), (mob, 'Mobile Arm', out_path_mob)]:
        abn = [r for r in records if r.get('anomaly_Label')]
        views = [v for v in ALL_VIEWS if any(r['views'] == v for r in abn)]
        pts = list(range(1, 12))
        data = [(r['views'], int(re.search(r'/point(\d+)/',r['image_id']).group(1)))
                for r in abn if re.search(r'/point(\d+)/',r['image_id'])]
        df = pd.DataFrame(data, columns=['view','point'])
        pivot = df.pivot_table(index='view', columns='point', aggfunc='size', fill_value=0)
        pivot = pivot.reindex(index=views, columns=pts, fill_value=0)
        fig, ax = plt.subplots(figsize=(10, 6))
        im = ax.imshow(pivot, aspect='auto', cmap='Blues')
        ax.set_xticks(np.arange(len(pts)))
        ax.set_xticklabels(pts)
        ax.set_yticks(np.arange(len(views)))
        ax.set_yticklabels(views)
        ax.set_xlabel('Point')
        ax.set_ylabel('View')
        ax.set_title(f'{label} Abnormal Count by View and Point', pad=20)
        ax.grid(True, linestyle='--')
        fig.colorbar(im, ax=ax, label='Abnormal Count', fraction=0.046, pad=0.04)
        fig.tight_layout()
        fig.savefig(path, dpi=300)
        plt.close(fig)

def plot_anomaly_types_radar_split(fix, mob, out_fix: Path, out_mob: Path):
    """Generate two radar charts of anomaly types per view: one for Fix Arm, one for Mobile Arm"""
    # Prepare views and types
    records_fix = [r for r in fix if r.get('anomaly_Label')]
    records_mob = [r for r in mob if r.get('anomaly_Label')]
    views = [v for v in VIEWS_ORDER if any(r['views']==v for r in records_fix+records_mob)]
    types = sorted({r['anomaly_Type'] for r in records_fix+records_mob})
    angles = np.linspace(0, 2*np.pi, len(views), endpoint=False).tolist() + [0]
     # counts per type per view
    cnt_fix={t:[sum(1 for r in records_fix if r['views']==v and r['anomaly_Type']==t) for v in views] for t in types}
    cnt_mob={t:[sum(1 for r in records_mob if r['views']==v and r['anomaly_Type']==t) for v in views] for t in types}
    # plot fix
    fig,ax=plt.subplots(subplot_kw=dict(polar=True),figsize=(8,6))
    cmap=plt.get_cmap('tab10')
    for i,t in enumerate(types):
        vals=cnt_fix[t]+[cnt_fix[t][0]]
        ax.plot(angles,vals,color=cmap(i),linewidth=2,label=t)
        ax.fill(angles,vals,color=cmap(i),alpha=0.25)
    ax.set_xticks(angles[:-1]);ax.set_xticklabels(views,fontsize=8)
    ax.set_title('Anomaly Types per View (Fix Arm)',pad=20)
    ax.legend(loc='upper right',bbox_to_anchor=(1.3,1.1),fontsize=7)
    fig.tight_layout();fig.savefig(out_fix,dpi=300);plt.close(fig)
    # plot mob
    fig,ax=plt.subplots(subplot_kw=dict(polar=True),figsize=(8,6))
    for i,t in enumerate(types):
        vals=cnt_mob[t]+[cnt_mob[t][0]]
        ax.plot(angles,vals,color=cmap(i),linewidth=2,label=t)
        ax.fill(angles,vals,color=cmap(i),alpha=0.25)
    ax.set_xticks(angles[:-1]);ax.set_xticklabels(views,fontsize=8)
    ax.set_title('Anomaly Types per View (Mobile Arm)',pad=20)
    ax.legend(loc='upper right',bbox_to_anchor=(1.3,1.1),fontsize=7)
    fig.tight_layout();fig.savefig(out_mob,dpi=300);plt.close(fig)


def main():
    root = Path(__file__).parent.parent
    ann = root.joinpath('data','annotation')
    plot = root.joinpath('data','plot')
    plot.mkdir(parents=True, exist_ok=True)

    fix,mob = load_records(ann.joinpath('records_fix_arm.json'), ann.joinpath('records_mobile_arm.json'))

    plot_combined_radar(fix, mob, plot.joinpath('combined_abn_norm_radar.png'))
    plot_anomaly_types_radar(fix, mob, plot.joinpath('anomaly_types_views_radar.png'))
    plot_bubble_color(fix, mob, plot.joinpath('bubble_color_point_type.png'))
    plot_heatmap_ordered(fix, mob, plot.joinpath('heatmap_abn_view_point_ordered.png'))
# split heatmaps for Fix and Mobile
    plot_heatmap_split(
        fix, mob,
        plot.joinpath('heatmap_fix_abn_view_point.png'),
        plot.joinpath('heatmap_mob_abn_view_point.png')
    )
    # after plot_heatmap_split(...)
    plot_anomaly_types_radar_split(
        fix, mob,
        plot.joinpath('anomaly_types_views_radar_fix.png'),
        plot.joinpath('anomaly_types_views_radar_mob.png')
    )
if __name__=='__main__':
    main()
