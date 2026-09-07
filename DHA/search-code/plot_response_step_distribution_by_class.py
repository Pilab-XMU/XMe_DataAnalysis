from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


INPUT_CSV = Path(
    "1_2279_ackley_response_outputs_run1000/response_steps_long_by_class.csv"
)
OUTPUT_DIR = Path("main_result_panels/response_step_by_class")
OUTPUT_PNG = OUTPUT_DIR / "response_step_probability_by_class.png"
OUTPUT_KDE_PNG = OUTPUT_DIR / "response_step_probability_by_class_kde.png"
OUTPUT_HIST_ONLY_PNG = OUTPUT_DIR / "response_step_probability_by_class_hist_only.png"
OUTPUT_HIST_ONLY_COUNTS_PNG = OUTPUT_DIR / "response_step_counts_by_class_hist_only.png"
OUTPUT_RIDGELINE_PNG = OUTPUT_DIR / "response_step_probability_by_class_ridgeline.png"
OUTPUT_CSV = OUTPUT_DIR / "response_step_probability_by_class.csv"
OUTPUT_HIST_ONLY_CSV = OUTPUT_DIR / "response_step_probability_by_class_hist_only.csv"
OUTPUT_HIST_ONLY_COUNTS_CSV = OUTPUT_DIR / "response_step_counts_by_class_hist_only.csv"
OUTPUT_RIDGELINE_CSV = OUTPUT_DIR / "response_step_probability_by_class_ridgeline.csv"
OUTPUT_FIT_CSV = OUTPUT_DIR / "gaussian_fit_probability_by_class.csv"
OUTPUT_KDE_CSV = OUTPUT_DIR / "kde_probability_by_class.csv"
SUMMARY_CSV = OUTPUT_DIR / "response_step_by_class_summary.csv"
BINS = 36
HIST_ONLY_BINS = 36

CLASS_ORDER = ["HLH", "HHL", "HHH", "HLL"]
RIDGELINE_TOP_TO_BOTTOM = ["HLH", "HHL", "HHH", "HLL"]
CLASS_LABELS = {
    "HLH": "HLH",
    "HHL": "HHL",
    "HHH": "HHH",
    "HLL": "HLL",
}

CLASS_COLORS = {
    "HLH": "#E6C85A",  # yellow
    "HHL": "#9387C9",  # purple
    "HHH": "#4FA398",  # green
    "HLL": "#4A9FD8",  # blue
}
LINE_COLORS = {
    "HLH": "#A87500",
    "HHL": "#5D4E9F",
    "HHH": "#1F7169",
    "HLL": "#176AAB",
}


def load_step_data(input_csv: Path) -> pd.DataFrame:
    df = pd.read_csv(input_csv)
    required = {"class_name", "step"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")

    df = df.loc[:, ["class_name", "step"]].copy()
    df["class_name"] = df["class_name"].astype(str)
    df["step"] = pd.to_numeric(df["step"], errors="coerce")
    df = df.dropna(subset=["class_name", "step"])
    df = df[df["step"] >= 0]

    unknown = sorted(set(df["class_name"]) - set(CLASS_ORDER))
    if unknown:
        raise ValueError(f"Unexpected class_name values: {unknown}")
    return df


def build_probability_histogram(
    df: pd.DataFrame,
    bins: int = BINS,
) -> pd.DataFrame:
    max_step = float(df["step"].max())
    bin_edges = np.linspace(0.0, max_step, bins + 1)
    records: list[dict[str, float | str | int]] = []

    for class_name in CLASS_ORDER:
        values = df.loc[df["class_name"] == class_name, "step"].to_numpy()
        counts, _ = np.histogram(values, bins=bin_edges)
        probabilities = counts / counts.sum()

        for left, right, count, probability in zip(
            bin_edges[:-1],
            bin_edges[1:],
            counts,
            probabilities,
        ):
            records.append(
                {
                    "class_name": class_name,
                    "bin_left": left,
                    "bin_right": right,
                    "bin_center": (left + right) / 2,
                    "count": int(count),
                    "probability": float(probability),
                }
            )

    return pd.DataFrame.from_records(records)


def build_gaussian_fit_curves(df: pd.DataFrame, hist_df: pd.DataFrame) -> pd.DataFrame:
    max_step = float(hist_df["bin_right"].max())
    bin_width = float(hist_df["bin_right"].iloc[0] - hist_df["bin_left"].iloc[0])
    x_grid = np.linspace(0.0, max_step, 600)
    records: list[dict[str, float | str]] = []

    for class_name in CLASS_ORDER:
        values = df.loc[df["class_name"] == class_name, "step"].to_numpy()
        mu = float(values.mean())
        sigma = float(values.std(ddof=1))
        if sigma <= 0:
            continue

        density = (
            np.exp(-0.5 * ((x_grid - mu) / sigma) ** 2)
            / (sigma * np.sqrt(2.0 * np.pi))
        )
        probability_per_bin = density * bin_width
        for x_value, probability in zip(x_grid, probability_per_bin):
            records.append(
                {
                    "class_name": class_name,
                    "step": float(x_value),
                    "gaussian_fit_probability": float(probability),
                    "mean": mu,
                    "std": sigma,
                    "bin_width": bin_width,
                }
            )

    return pd.DataFrame.from_records(records)


def silverman_bandwidth(values: np.ndarray) -> float:
    n = len(values)
    if n < 2:
        return 1.0

    std = float(np.std(values, ddof=1))
    iqr = float(np.quantile(values, 0.75) - np.quantile(values, 0.25))
    robust_sigma = min(std, iqr / 1.349) if iqr > 0 else std
    bandwidth = 0.9 * robust_sigma * n ** (-1 / 5)
    return max(bandwidth, 1e-6)


def build_reflected_kde_curves(df: pd.DataFrame, hist_df: pd.DataFrame) -> pd.DataFrame:
    max_step = float(hist_df["bin_right"].max())
    bin_width = float(hist_df["bin_right"].iloc[0] - hist_df["bin_left"].iloc[0])
    x_grid = np.linspace(0.0, max_step, 600)
    records: list[dict[str, float | str]] = []

    for class_name in CLASS_ORDER:
        values = df.loc[df["class_name"] == class_name, "step"].to_numpy()
        bandwidth = silverman_bandwidth(values)
        z_pos = (x_grid[:, None] - values[None, :]) / bandwidth
        z_reflect = (x_grid[:, None] + values[None, :]) / bandwidth
        density = (
            np.exp(-0.5 * z_pos**2).mean(axis=1)
            + np.exp(-0.5 * z_reflect**2).mean(axis=1)
        ) / (bandwidth * np.sqrt(2.0 * np.pi))
        probability_per_bin = density * bin_width

        for x_value, probability in zip(x_grid, probability_per_bin):
            records.append(
                {
                    "class_name": class_name,
                    "step": float(x_value),
                    "kde_probability": float(probability),
                    "bandwidth": bandwidth,
                    "bin_width": bin_width,
                }
            )

    return pd.DataFrame.from_records(records)


def summarize_steps(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("class_name")["step"]
        .agg(
            count="count",
            min="min",
            q25=lambda s: s.quantile(0.25),
            median="median",
            q75=lambda s: s.quantile(0.75),
            mean="mean",
            std="std",
            max="max",
        )
        .reindex(CLASS_ORDER)
        .reset_index()
    )


def plot_probability_histogram(
    hist_df: pd.DataFrame,
    fit_df: pd.DataFrame,
    output_png: Path,
    curve_column: str = "gaussian_fit_probability",
) -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 10,
            "axes.linewidth": 0.8,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, ax = plt.subplots(figsize=(4.6, 3.2), dpi=300)

    for class_name in CLASS_ORDER:
        part = hist_df[hist_df["class_name"] == class_name]
        fit_part = fit_df[fit_df["class_name"] == class_name]
        x = part["bin_center"].to_numpy()
        y = part["probability"].to_numpy()
        width = float(part["bin_right"].iloc[0] - part["bin_left"].iloc[0])

        ax.bar(
            x,
            y,
            width=width * 0.82,
            color=CLASS_COLORS[class_name],
            alpha=0.46,
            edgecolor="none",
            align="center",
        )
        ax.plot(
            fit_part["step"].to_numpy(),
            fit_part[curve_column].to_numpy(),
            color=LINE_COLORS[class_name],
            linewidth=2.2,
            label=CLASS_LABELS[class_name],
        )

    ax.set_xlabel("Response step")
    ax.set_ylabel("Probability")
    ax.set_xlim(0, hist_df["bin_right"].max())
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, handlelength=2.4, borderaxespad=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3.5)

    fig.tight_layout(pad=0.4)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, transparent=True)
    plt.close(fig)


def plot_hist_only(
    hist_df: pd.DataFrame,
    output_png: Path,
    value_column: str = "probability",
    ylabel: str = "Probability",
) -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 10,
            "axes.linewidth": 0.8,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, ax = plt.subplots(figsize=(4.6, 3.2), dpi=300)

    for class_name in CLASS_ORDER:
        part = hist_df[hist_df["class_name"] == class_name]
        x = part["bin_center"].to_numpy()
        y = part[value_column].to_numpy()
        width = float(part["bin_right"].iloc[0] - part["bin_left"].iloc[0])

        ax.bar(
            x,
            y,
            width=width * 0.98,
            color=CLASS_COLORS[class_name],
            alpha=0.82,
            edgecolor="none",
            align="center",
            label=CLASS_LABELS[class_name],
        )

    ax.set_xlabel("Response step")
    ax.set_ylabel(ylabel)
    ax.set_xlim(0, hist_df["bin_right"].max())
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, handlelength=1.8, borderaxespad=0.2)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3.5)

    fig.tight_layout(pad=0.4)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, transparent=True)
    plt.close(fig)


def build_ridgeline_data(hist_df: pd.DataFrame) -> pd.DataFrame:
    max_probability = float(hist_df["probability"].max())
    offset_step = max_probability * 1.12
    records: list[dict[str, float | str]] = []

    bottom_to_top = list(reversed(RIDGELINE_TOP_TO_BOTTOM))
    for index, class_name in enumerate(bottom_to_top):
        part = hist_df[hist_df["class_name"] == class_name]
        offset = index * offset_step
        for row in part.itertuples(index=False):
            records.append(
                {
                    "class_name": class_name,
                    "bin_center": float(row.bin_center),
                    "probability": float(row.probability),
                    "offset": float(offset),
                    "offset_probability": float(row.probability + offset),
                }
            )

    return pd.DataFrame.from_records(records)


def plot_ridgeline_frequency_polygon(
    hist_df: pd.DataFrame,
    ridgeline_df: pd.DataFrame,
    output_png: Path,
) -> None:
    plt.rcParams.update(
        {
            "font.family": "Arial",
            "font.size": 10,
            "axes.linewidth": 0.8,
            "xtick.major.width": 0.8,
            "ytick.major.width": 0.8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    fig, ax = plt.subplots(figsize=(4.6, 3.35), dpi=300)
    y_ticks = []
    y_labels = []

    for class_name in reversed(RIDGELINE_TOP_TO_BOTTOM):
        part = hist_df[hist_df["class_name"] == class_name]
        ridge_part = ridgeline_df[ridgeline_df["class_name"] == class_name]
        x_centers = ridge_part["bin_center"].to_numpy()
        probabilities = ridge_part["probability"].to_numpy()
        offset = float(ridge_part["offset"].iloc[0])
        left_edge = float(part["bin_left"].iloc[0])
        right_edge = float(part["bin_right"].iloc[-1])

        x = np.r_[left_edge, x_centers, right_edge]
        y = np.r_[0.0, probabilities, 0.0] + offset
        baseline = np.full_like(x, offset)

        ax.fill_between(
            x,
            baseline,
            y,
            color=CLASS_COLORS[class_name],
            alpha=0.62,
            linewidth=0,
        )
        ax.plot(
            x,
            y,
            color=LINE_COLORS[class_name],
            linewidth=1.55,
        )
        y_ticks.append(offset)
        y_labels.append(CLASS_LABELS[class_name])

    ax.set_xlabel("Response step")
    ax.set_ylabel("Class")
    ax.set_xlim(0, hist_df["bin_right"].max())
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels)
    ax.set_ylim(-0.02, max(y_ticks) + float(hist_df["probability"].max()) * 1.18)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(direction="out", length=3.5)

    fig.tight_layout(pad=0.4)
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png, transparent=True)
    plt.close(fig)


def main() -> None:
    df = load_step_data(INPUT_CSV)
    hist_df = build_probability_histogram(df)
    hist_only_df = build_probability_histogram(df, bins=HIST_ONLY_BINS)
    ridgeline_df = build_ridgeline_data(hist_only_df)
    fit_df = build_gaussian_fit_curves(df, hist_df)
    kde_df = build_reflected_kde_curves(df, hist_df)
    summary_df = summarize_steps(df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    hist_df.to_csv(OUTPUT_CSV, index=False)
    hist_only_df.to_csv(OUTPUT_HIST_ONLY_CSV, index=False)
    hist_only_df.to_csv(OUTPUT_HIST_ONLY_COUNTS_CSV, index=False)
    ridgeline_df.to_csv(OUTPUT_RIDGELINE_CSV, index=False)
    fit_df.to_csv(OUTPUT_FIT_CSV, index=False)
    kde_df.to_csv(OUTPUT_KDE_CSV, index=False)
    summary_df.to_csv(SUMMARY_CSV, index=False)
    plot_probability_histogram(hist_df, fit_df, OUTPUT_PNG)
    plot_probability_histogram(
        hist_df,
        kde_df,
        OUTPUT_KDE_PNG,
        curve_column="kde_probability",
    )
    plot_hist_only(hist_only_df, OUTPUT_HIST_ONLY_PNG)
    plot_hist_only(
        hist_only_df,
        OUTPUT_HIST_ONLY_COUNTS_PNG,
        value_column="count",
        ylabel="Count",
    )
    plot_ridgeline_frequency_polygon(hist_only_df, ridgeline_df, OUTPUT_RIDGELINE_PNG)

    print(f"Saved figure: {OUTPUT_PNG}")
    print(f"Saved KDE figure: {OUTPUT_KDE_PNG}")
    print(f"Saved hist-only figure: {OUTPUT_HIST_ONLY_PNG}")
    print(f"Saved hist-only counts figure: {OUTPUT_HIST_ONLY_COUNTS_PNG}")
    print(f"Saved ridgeline figure: {OUTPUT_RIDGELINE_PNG}")
    print(f"Saved histogram data: {OUTPUT_CSV}")
    print(f"Saved hist-only data: {OUTPUT_HIST_ONLY_CSV}")
    print(f"Saved hist-only counts data: {OUTPUT_HIST_ONLY_COUNTS_CSV}")
    print(f"Saved ridgeline data: {OUTPUT_RIDGELINE_CSV}")
    print(f"Saved Gaussian fit data: {OUTPUT_FIT_CSV}")
    print(f"Saved KDE data: {OUTPUT_KDE_CSV}")
    print(f"Saved summary: {SUMMARY_CSV}")


if __name__ == "__main__":
    main()
