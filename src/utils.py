import json
import os
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def prepare():
    from pathlib import Path
    import sys

    PROJECT_ROOT = next(
        parent for parent in (Path.cwd(), *Path.cwd().parents) if (parent / "config" / "paths.py").is_file()
    )
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from config.paths import DATA_DIR, MANIFEST_FILE

    return PROJECT_ROOT, DATA_DIR, MANIFEST_FILE


def load_manifest(file_path):
    """_summary_

    Returns:
        _type_: _description_
    """

    with open(
        file_path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def load_clubs(file_path):
    with (file_path).open() as f:
        clubs = json.load(f)
    return clubs


def compute_ranking(data_dir, manifest):
    clubs = load_clubs(data_dir / manifest["clubs"])
    season_ranks = {}
    for league, competition in manifest["competition"].items():
        rank_offset = 18 if league == "league_2" else 0
        for season in competition["seasons"]:
            with (data_dir / season["ranking_file"]).open() as f:
                ranking = json.load(f)
            season_ranks.setdefault(season["year"], {}).update(
                {club_id: result["season"] + rank_offset for club_id, result in ranking.items()}
            )

    rank_df = pd.DataFrame.from_dict(season_ranks, orient="index").sort_index()
    rank_df.index.name = "Season"
    rank_df = rank_df.reindex(columns=clubs.keys(), fill_value=np.nan).T
    rank_df.index.name = "Club ID"
    return rank_df


def compute_running_average(rank_df, years=None):
    """Return each club's running average for the selected years."""
    selected_rank_df = rank_df.loc[:, years] if years is not None else rank_df
    missing_rank = selected_rank_df.max(axis=0).add(1)
    average_rank_df = selected_rank_df.where(selected_rank_df.notna(), missing_rank, axis="columns")
    return average_rank_df.T.expanding(min_periods=1).mean().T


def compute_running_average_ranking(rank_df, years=None):
    """Return each club's discrete rank by running average for the selected years."""
    running_average_df = compute_running_average(rank_df, years)
    return running_average_df.rank(axis=0, method="min", ascending=True).astype(int)


def plot_final_results(rank_df, clubs, years=None):
    fig, ax = plt.subplots(figsize=(14, 10))
    selected_rank_df = rank_df.loc[:, years] if years is not None else rank_df
    for club_id, club in clubs.items():
        club_results = selected_rank_df.loc[club_id].dropna()
        ax.plot(
            club_results.index,
            club_results,
            marker="o",
            label=clubs[club_id]["short"],
            color=clubs[club_id]["color"],
        )
        last_season = club_results.last_valid_index()
        if last_season is not None:
            ax.annotate(
                club["short"],
                xy=(last_season, club_results.loc[last_season]),
                xytext=(5, 0),
                textcoords="offset points",
                va="center",
                color=club["color"],
            )
    ax.set_title("Final season rank across both leagues per club")
    ax.set_xlabel("Season")
    ax.set_ylabel("Final rank")
    ax.set_yticks(np.arange(1, 37))
    ax.invert_yaxis()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig, ax


def plot_alltime_average(rank_df, clubs, years=None):
    running_average_df = compute_running_average(rank_df, years)

    fig, ax = plt.subplots(figsize=(14, 10))
    for club_id, club in clubs.items():
        ax.plot(
            running_average_df.columns,
            running_average_df.loc[club_id],
            marker="o",
            label=club["short"],
            color=club["color"],
        )
        last_season = running_average_df.loc[club_id].last_valid_index()
        if last_season is not None:
            ax.annotate(
                club["short"],
                xy=(last_season, running_average_df.loc[club_id, last_season]),
                xytext=(5, 0),
                textcoords="offset points",
                va="center",
                color=club["color"],
            )

    ax.set_title("Ewige Bestenliste Segelbundesliga")
    ax.set_xlabel("Jahr")
    ax.set_ylabel("Durchschnittliche Platzierung")
    ax.set_ylim(37.5, 0.5)
    ax.set_yticks([1, 5, 10, 15, 20, 25, 30, 35])
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig, ax


def plot_alltime_average_ranking(rank_df, clubs, years=None):
    ranking_df = compute_running_average_ranking(rank_df, years)
    last_year = ranking_df.columns[-1]
    clubs_by_last_rank = {}
    for club_id in ranking_df.index:
        last_rank = ranking_df.loc[club_id, last_year]
        clubs_by_last_rank.setdefault(last_rank, []).append(club_id)

    annotation_offsets = {}
    for club_ids in clubs_by_last_rank.values():
        for position, club_id in enumerate(club_ids):
            annotation_offsets[club_id] = 5 + position * 35

    fig, ax = plt.subplots(figsize=(14, 10))
    for club_id, club in clubs.items():
        ax.plot(
            ranking_df.columns,
            ranking_df.loc[club_id],
            marker="o",
            label=club["short"],
            color=club["color"],
        )
        last_season = ranking_df.loc[club_id].last_valid_index()
        if last_season is not None:
            ax.annotate(
                club["short"],
                xy=(last_season, ranking_df.loc[club_id, last_season]),
                xytext=(annotation_offsets[club_id], 0),
                textcoords="offset points",
                va="center",
                color=club["color"],
            )

    ax.set_title("Ewige Bestenliste")
    ax.set_xlabel("Jahr")
    ax.set_ylabel("Platzierung")
    ax.set_ylim(len(clubs) + 0.5, 0.5)
    ax.set_yticks(np.arange(1, len(clubs) + 1, 5))
    ax.set_xticks(ranking_df.columns)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    return fig, ax


def plot_season(data_dir, manifest, clubs, year):
    fig, axes = plt.subplots(2, 1, figsize=(14, 16), sharex=True)

    for ax, league, title in zip(
        axes,
        ("league_1", "league_2"),
        ("League 1", "League 2"),
    ):
        active_season = next(
            active_season
            for active_season in manifest["competition"][league]["seasons"]
            if active_season["year"] == year
        )
        with (data_dir / active_season["ranking_file"]).open() as f:
            ranking = json.load(f)

        event_ranks = pd.DataFrame.from_dict(ranking, orient="index").loc[:, "events"].apply(pd.Series)
        event_ranks.columns = np.arange(1, len(event_ranks.columns) + 1)
        running_average_ranks = event_ranks.T.expanding(min_periods=1).mean().T
        average_ax = ax.twinx()

        for club_id in event_ranks.index:
            club = clubs[club_id]
            label = club["short"]
            ax.plot(
                event_ranks.columns,
                event_ranks.loc[club_id],
                color=club["color"],
                label=label,
                marker="o",
            )
            average_ax.plot(
                running_average_ranks.columns,
                running_average_ranks.loc[club_id],
                color=club["color"],
                linestyle="--",
                marker="o",
            )

        ax.set_title(manifest["competition"][league]["name"] + f" {year}")
        ax.set_ylabel("Platzierung")
        average_ax.set_ylabel("Durchschnitts Platzierung")
        ax.set_ylim(0, len(event_ranks) + 1)
        ax.set_yticks(np.arange(1, len(event_ranks) + 1))
        average_ax.set_ylim(0, len(event_ranks) + 1)
        average_ax.set_yticks(np.arange(1, len(event_ranks) + 1))
        ax.invert_yaxis()
        average_ax.invert_yaxis()
        ax.grid(axis="y", alpha=0.3, linestyle="--")
        ax.grid(
            axis="x",
        )
        handles, labels = ax.get_legend_handles_labels()
        average_handles, average_labels = average_ax.get_legend_handles_labels()
        ax.legend(
            handles + average_handles,
            labels + average_labels,
            bbox_to_anchor=(1.1, 0.5),
            loc="center left",
            title="Endstand",
        )

    axes[-1].set_xlabel("Event")
    fig.suptitle(f"Saison {year}", fontsize=16)
    fig.tight_layout(rect=(0, 0, 0.92, 0.97))
    return fig, axes
