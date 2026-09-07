"""Create revised standalone paper figures without replacing earlier outputs."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd


BASE_SCRIPT = Path(__file__).with_name("plot_step_range_kernel_paper_figures.py")
BASE_SPEC = importlib.util.spec_from_file_location("_step_range_paper_figures_base", BASE_SCRIPT)
base = importlib.util.module_from_spec(BASE_SPEC)
sys.modules[BASE_SPEC.name] = base
BASE_SPEC.loader.exec_module(base)

OUTPUT_DIR = base.RESULTS_DIR / "paper_figures_revised"
CURVE_BINS = 60
FIGURE_DPI = 300
FINAL_VALUE_FUNCTIONS = ("rastrigin", "rosenbrock", "ackley")
PNG_OUTPUTS = {
    "curve_0_05": "sampling_kernel_step_distribution_0_5_to_1_0_nm_revised.png",
    "curve_05_10": "sampling_kernel_step_distribution_1_0_to_1_5_nm_revised.png",
    "curve_10_15": "sampling_kernel_step_distribution_1_5_to_2_0_nm_revised.png",
    "curve_15_20": "sampling_kernel_step_distribution_2_0_to_2_5_nm_revised.png",
    "rastrigin_success": "rastrigin_budget10000_success_le_0p1_revised.png",
    "rastrigin_final": "rastrigin_budget10000_final_value_distribution_revised.png",
    "rosenbrock_final": "rosenbrock_budget10000_final_value_distribution_revised.png",
    "ackley_final": "ackley_budget10000_final_value_distribution_revised.png",
}
OLD_PNG_NAMES = {
    path.name for path in (base.RESULTS_DIR / "paper_figures").glob("*.png")
}


def build_probability_curves(
    step_data: pd.DataFrame,
    bins: int = CURVE_BINS,
) -> pd.DataFrame:
    required = {"step_range", "sE"}
    if not required.issubset(step_data.columns):
        raise ValueError(f"step_data must contain {sorted(required)}")
    max_step = float(step_data["sE"].max())
    if bins <= 0 or not np.isfinite(max_step) or max_step <= 0:
        raise ValueError("bins and response steps must define a positive finite range")

    edges = np.linspace(0.0, max_step, bins + 1)
    records = []
    for step_range in base.STEP_RANGES:
        values = step_data.loc[step_data["step_range"] == step_range, "sE"].to_numpy(dtype=float)
        if len(values) == 0:
            raise ValueError(f"No response steps found for {step_range}")
        counts, _ = np.histogram(values, bins=edges)
        probabilities = counts / counts.sum()
        for left, right, count, probability in zip(
            edges[:-1], edges[1:], counts, probabilities
        ):
            records.append(
                {
                    "step_range": step_range,
                    "step_length_nm": base.RANGE_LABELS[step_range],
                    "bin_left": float(left),
                    "bin_right": float(right),
                    "bin_center": float((left + right) / 2),
                    "count": int(count),
                    "probability": float(probability),
                    "n_steps": int(len(values)),
                }
            )
    return pd.DataFrame(records)


def shared_curve_y_limit(curves: pd.DataFrame) -> float:
    maximum = float(curves["probability"].max())
    if not np.isfinite(maximum) or maximum <= 0:
        raise ValueError("curves must contain positive finite probabilities")
    return maximum * 1.05


def save_transparent(fig: plt.Figure, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(
        output_path,
        dpi=FIGURE_DPI,
        transparent=True,
        facecolor="none",
        bbox_inches="tight",
        pad_inches=0.04,
    )
    plt.close(fig)


def plot_step_curve(
    curve: pd.DataFrame,
    step_range: str,
    output_path: Path,
    y_max: float,
) -> None:
    if len(curve) == 0 or curve["step_range"].nunique() != 1:
        raise ValueError("curve must contain one non-empty physical step range")
    x = curve["bin_center"].to_numpy(dtype=float)
    y = curve["probability"].to_numpy(dtype=float)
    left = float(curve["bin_left"].iloc[0])
    right = float(curve["bin_right"].iloc[-1])
    n_steps = int(curve["n_steps"].iloc[0])

    fig, ax = plt.subplots(figsize=(4.35, 3.25))
    ax.plot(x, y, color=base.COLORS[step_range], linewidth=1.5)
    ax.fill_between(x, 0, y, color=base.COLORS[step_range], alpha=0.14, linewidth=0)
    ax.set_xlabel("Response-step magnitude")
    ax.set_ylabel("Probability per bin")
    ax.set_xlim(left, right)
    ax.set_ylim(0, y_max)
    ax.legend(
        [f"{base.RANGE_LABELS[step_range]} nm (n={n_steps})"],
        title="Physical step-length regime",
        frameon=False,
        loc="upper right",
        handlelength=0,
        handletextpad=0,
    )
    base.style_axes(ax)
    fig.tight_layout(pad=0.35)
    save_transparent(fig, output_path)


def plot_rastrigin_success(success_data: pd.DataFrame, output_path: Path) -> None:
    if len(success_data) != len(base.STEP_RANGES):
        raise ValueError("Expected one Rastrigin success-rate row per kernel")
    fig, ax = plt.subplots(figsize=(4.35, 3.25))
    x = np.arange(len(base.STEP_RANGES))
    rates = success_data["success_rate"].to_numpy(dtype=float)
    lower = rates - success_data["ci_low"].to_numpy(dtype=float)
    upper = success_data["ci_high"].to_numpy(dtype=float) - rates
    for index, step_range in enumerate(base.STEP_RANGES):
        ax.errorbar(
            x[index],
            rates[index],
            yerr=np.array([[lower[index]], [upper[index]]]),
            fmt="o",
            color=base.COLORS[step_range],
            markeredgecolor="white",
            markeredgewidth=0.55,
            markersize=4.2,
            elinewidth=1.15,
            capsize=3,
            zorder=3,
        )
    ax.set_xticks(x, [base.RANGE_LABELS[step_range] for step_range in base.STEP_RANGES])
    ax.set_xlabel("Physical step-length regime (nm)")
    ax.set_ylabel("Success rate")
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.set_ylim(0.6, 1.0)
    ax.set_yticks(np.arange(0.6, 1.01, 0.1))
    base.style_axes(ax)
    fig.tight_layout(pad=0.35)
    save_transparent(fig, output_path)


def plot_final_value_boxplot(
    runs: pd.DataFrame,
    function_name: str,
    output_path: Path,
) -> None:
    selected = runs.loc[
        (runs["function"] == function_name) & (runs["budget"] == 10000)
    ]
    data = [
        selected.loc[selected["source"] == step_range, "final_best"].to_numpy(dtype=float)
        for step_range in base.STEP_RANGES
    ]
    if any(len(values) == 0 for values in data) or any(
        np.any(values <= 0) for values in data
    ):
        raise ValueError(
            f"{function_name} final values must be present and positive for logarithmic plotting"
        )

    fig, ax = plt.subplots(figsize=(4.35, 3.25))
    box = ax.boxplot(
        data,
        patch_artist=True,
        widths=0.58,
        whis=(5, 95),
        showfliers=False,
        showmeans=True,
        medianprops={"color": "#202020", "linewidth": 1.35},
        meanprops={
            "marker": "D",
            "markerfacecolor": "white",
            "markeredgecolor": "#202020",
            "markeredgewidth": 0.75,
            "markersize": 4.0,
            "zorder": 10,
        },
        whiskerprops={"color": "#555555", "linewidth": 0.9},
        capprops={"color": "#555555", "linewidth": 0.9},
    )
    for patch, step_range in zip(box["boxes"], base.STEP_RANGES):
        patch.set_facecolor(base.COLORS[step_range])
        patch.set_alpha(0.58)
        patch.set_edgecolor(base.COLORS[step_range])
        patch.set_linewidth(1.0)
    ax.set_xticks(
        np.arange(1, 5),
        [base.RANGE_LABELS[step_range] for step_range in base.STEP_RANGES],
    )
    ax.set_xlabel("Physical step-length regime (nm)")
    ax.set_ylabel("Final objective value")
    ax.set_yscale("log")
    ax.legend(
        handles=[
            Line2D([0], [0], color="#202020", linewidth=1.35, label="Median"),
            Line2D(
                [0],
                [0],
                marker="D",
                color="none",
                markerfacecolor="white",
                markeredgecolor="#202020",
                markersize=4.5,
                label="Mean",
            ),
        ],
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.5, 1.015),
        ncol=2,
        borderaxespad=0.0,
        handlelength=1.4,
    )
    base.style_axes(ax)
    fig.tight_layout(pad=0.35)
    save_transparent(fig, output_path)


def main() -> None:
    base.configure_style()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    step_data = base.load_step_data()
    curves = build_probability_curves(step_data)
    curve_y_max = shared_curve_y_limit(curves)
    for step_range in base.STEP_RANGES:
        key = f"curve_{step_range}"
        png_path = OUTPUT_DIR / PNG_OUTPUTS[key]
        curve = curves.loc[curves["step_range"] == step_range].copy()
        curve.to_csv(png_path.with_suffix(".csv"), index=False)
        plot_step_curve(curve, step_range, png_path, y_max=curve_y_max)

    success_summary = pd.read_csv(base.SUCCESS_CSV)
    success_data = base.build_rastrigin_success_data(success_summary)
    success_path = OUTPUT_DIR / PNG_OUTPUTS["rastrigin_success"]
    success_data.to_csv(success_path.with_suffix(".csv"), index=False)
    plot_rastrigin_success(success_data, success_path)

    runs = base.load_final_runs()
    for function_name in FINAL_VALUE_FUNCTIONS:
        summary = base.summarize_final_values(runs, function_name)
        png_path = OUTPUT_DIR / PNG_OUTPUTS[f"{function_name}_final"]
        summary.to_csv(png_path.with_suffix(".csv"), index=False)
        plot_final_value_boxplot(runs, function_name, png_path)

    print(f"Wrote revised standalone paper figures to {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
