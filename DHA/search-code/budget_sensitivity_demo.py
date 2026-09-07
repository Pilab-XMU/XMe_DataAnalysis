"""
Budget-sensitivity benchmark for measured response-step distributions.

The script compares five step sources across Ackley, Rastrigin, Schwefel, and Rosenbrock:
    sampled_device, gaussian, uniform, truncated_device, rms_truncated_device

Outputs are written as PNG figures and CSV data only. The fitvalue-length CSVs
store median/IQR curves rather than every run-by-iteration value, keeping the
default 1000-run analysis tractable on disk.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Arial"
matplotlib.rcParams["mathtext.fontset"] = "dejavusans"
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
CACHE_DIR = BASE_DIR / "1_2279_ackley_response_outputs_run1000"
MEASURED_SEQUENCE_CSV = CACHE_DIR / "measured_operation_sequence_2279.csv"
TRACE_STEPS_CSV = CACHE_DIR / "response_steps_by_trace.csv"
SERIALS_CSV = BASE_DIR / "serials.csv"

DEFAULT_OUTPUT_DIR = BASE_DIR / "budget_10000_sensitivity_outputs"
DEFAULT_BUDGETS = [1000, 2279, 5000, 7500, 10000]
DEFAULT_N_RUNS = 10000
BASE_SEED = 25
ACCEPT_WORSE_PROB = 0.05
TRUNCATE_TOP_FRACTION = 0.10

SOURCES = ["sampled_device", "gaussian", "uniform", "truncated_device", "rms_truncated_device"]
SOURCE_LABELS = {
    "sampled_device": "sampled device",
    "gaussian": "RMS-matched Gaussian",
    "uniform": "RMS-matched Uniform",
    "truncated_device": "truncated device",
    "rms_truncated_device": "RMS-matched truncated device",
}
COLORS = {
    "sampled_device": "#0072B2",
    "gaussian": "#CC79A7",
    "uniform": "#009E73",
    "truncated_device": "#D55E00",
    "rms_truncated_device": "#E69F00",
}
LINESTYLES = {
    "sampled_device": "-",
    "gaussian": "--",
    "uniform": "-.",
    "truncated_device": ":",
    "rms_truncated_device": (0, (3, 1, 1, 1)),
}


@dataclass(frozen=True)
class FunctionSpec:
    name: str
    display_name: str
    objective: Callable[[float, float], float]
    search_lo: float
    search_hi: float
    start_pos: np.ndarray
    target_thresholds: tuple[float, ...]

    @property
    def start_value(self) -> float:
        return float(self.objective(float(self.start_pos[0]), float(self.start_pos[1])))


@dataclass
class SearchResult:
    best_values: np.ndarray
    accepted: np.ndarray
    clipped: np.ndarray


def ackley_2d(x: float, y: float) -> float:
    return float(
        -20 * np.exp(-0.2 * np.sqrt(0.5 * (x**2 + y**2)))
        - np.exp(0.5 * (np.cos(2 * np.pi * x) + np.cos(2 * np.pi * y)))
        + 20
        + np.e
    )


def rastrigin_2d(x: float, y: float) -> float:
    return float(20 + x**2 + y**2 - 10 * (np.cos(2 * np.pi * x) + np.cos(2 * np.pi * y)))


def schwefel_2d_scaled(x: float, y: float) -> float:
    z = np.array([x, y], dtype=float) * 100.0
    return float(418.9829 * 2 - np.sum(z * np.sin(np.sqrt(np.abs(z)))))

def rosenbrock_2d(x: float, y: float) -> float:
    return float(100 * (y - x**2) ** 2 + (1 - x) ** 2)

FUNCTIONS = {
    "rastrigin": FunctionSpec(
        name="rastrigin",
        display_name="Rastrigin",
        objective=rastrigin_2d,
        search_lo=-5.12,
        search_hi=5.12,
        start_pos=np.array([4.0, 4.0], dtype=float),
        target_thresholds=(0.0001,0.001,0.01,0.05,0.1, 1.0, 5.0,10.0),
    ),
    "schwefel": FunctionSpec(
        name="schwefel",
        display_name="Schwefel",
        objective=schwefel_2d_scaled,
        search_lo=-5.0,
        search_hi=5.0,
        start_pos=np.array([0.0, 0.0], dtype=float),
        target_thresholds=(0.1,1,10.0, 50.0, 100.0,200.0,500.0,1000.0),
    ),
    "ackley": FunctionSpec(
        name="ackley",
        display_name="Ackley",
        objective=ackley_2d,
        search_lo=-5.0,
        search_hi=5.0,
        start_pos=np.array([4.0, 4.0], dtype=float),
        target_thresholds=(0.00005,0.0001,0.0005, 0.001, 0.005, 0.01, 0.05, 0.1),
    ),
    "rosenbrock": FunctionSpec(
        name="rosenbrock",
        display_name="Rosenbrock",
        objective=rosenbrock_2d,
        search_lo=-2,
        search_hi=2,
        start_pos=np.array([-1.2,1.0], dtype=float),
        target_thresholds=(0.00001,0.00005,0.0001, 0.0005,0.001,0.005, 0.01, 0.05),
    )
}
FUNCTION_ORDER = ["rastrigin", "schwefel", "ackley", "rosenbrock"]


def rms(x: np.ndarray) -> float:
    values = np.asarray(x, dtype=float)
    return float(np.sqrt(np.mean(np.square(values))))


def scale_to_rms(raw: np.ndarray, target_rms: float) -> np.ndarray:
    raw_values = np.asarray(raw, dtype=float)
    raw_rms = rms(raw_values)
    if raw_rms <= 0:
        raise ValueError("raw sequence RMS must be positive")
    return raw_values * (target_rms / raw_rms)


def rms_matched_gaussian(
    reference_steps: np.ndarray,
    n_operations: int,
    rng: np.random.Generator,
) -> np.ndarray:
    raw = np.abs(rng.normal(0.0, 1.0, size=n_operations))
    return scale_to_rms(raw, rms(reference_steps))


def rms_matched_uniform(
    reference_steps: np.ndarray,
    n_operations: int,
    rng: np.random.Generator,
) -> np.ndarray:
    raw = rng.uniform(0.0, 1.0, size=n_operations)
    return scale_to_rms(raw, rms(reference_steps))


def load_serial_labels(path: Path = SERIALS_CSV) -> np.ndarray:
    df = pd.read_csv(path)
    if df.shape[1] < 2:
        raise ValueError("serials.csv must contain an index column and a class-label column")
    return df.iloc[:, 1].astype(int).to_numpy()


def load_step_inputs(
    measured_path: Path = MEASURED_SEQUENCE_CSV,
    trace_steps_path: Path = TRACE_STEPS_CSV,
    serials_path: Path = SERIALS_CSV,
) -> tuple[np.ndarray, pd.DataFrame, np.ndarray]:
    measured_steps = pd.read_csv(measured_path)["step"].to_numpy(dtype=float)
    trace_steps = pd.read_csv(trace_steps_path)
    labels = load_serial_labels(serials_path)
    return measured_steps, trace_steps, labels


def class_probabilities(labels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    class_ids, counts = np.unique(labels.astype(int), return_counts=True)
    probs = counts.astype(float) / float(np.sum(counts))
    return class_ids, probs


def sample_device_sequence(
    trace_steps: pd.DataFrame,
    labels: np.ndarray,
    n_operations: int,
    rng: np.random.Generator,
) -> np.ndarray:
    class_ids, probs = class_probabilities(labels)
    class_groups = {
        int(class_id): trace_steps.loc[trace_steps["class_id"] == int(class_id), "sE"].to_numpy(dtype=float)
        for class_id in class_ids
    }
    out = np.empty(n_operations, dtype=float)
    sampled_classes = rng.choice(class_ids, p=probs, size=n_operations)
    for class_id in class_ids:
        mask = sampled_classes == class_id
        if not np.any(mask):
            continue
        pool = class_groups[int(class_id)]
        out[mask] = pool[rng.integers(0, pool.size, size=int(np.sum(mask)))]
    return out


def truncated_device_sequence(
    reference_steps: np.ndarray,
    n_operations: int,
    rng: np.random.Generator,
    top_fraction: float = TRUNCATE_TOP_FRACTION,
) -> np.ndarray:
    cutoff = float(np.quantile(reference_steps, 1.0 - top_fraction))
    pool = np.asarray(reference_steps, dtype=float)[reference_steps <= cutoff]
    if pool.size == 0:
        raise ValueError("truncated device pool is empty")
    return rng.choice(pool, size=n_operations, replace=True)


def source_rng(base_seed: int, function_name: str, budget: int, run_idx: int, source_name: str) -> np.random.Generator:
    source_idx = SOURCES.index(source_name)
    function_idx = list(FUNCTIONS).index(function_name)
    seed_sequence = np.random.SeedSequence([base_seed, function_idx, budget, run_idx, source_idx])
    return np.random.default_rng(seed_sequence)


def build_step_sequence(
    source_name: str,
    measured_steps: np.ndarray,
    trace_steps: pd.DataFrame,
    labels: np.ndarray,
    n_operations: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if source_name == "sampled_device":
        return sample_device_sequence(trace_steps, labels, n_operations, rng)
    if source_name == "gaussian":
        return rms_matched_gaussian(measured_steps, n_operations, rng)
    if source_name == "uniform":
        return rms_matched_uniform(measured_steps, n_operations, rng)
    if source_name == "truncated_device":
        return truncated_device_sequence(measured_steps, n_operations, rng)
    if source_name == "rms_truncated_device":
        raw = truncated_device_sequence(measured_steps, n_operations, rng)
        return scale_to_rms(raw, rms(measured_steps))
    raise ValueError(f"unknown source: {source_name}")


def build_run_step_sequences(
    function_name: str,
    budget: int,
    run_idx: int,
    measured_steps: np.ndarray,
    trace_steps: pd.DataFrame,
    labels: np.ndarray,
    base_seed: int,
) -> dict[str, np.ndarray]:
    """Build all step-source sequences for one matched run.

    Gaussian, uniform, and RMS-truncated controls are RMS-matched to the
    sampled-device sequence from the same run and budget. The raw truncated
    control is not rescaled because it is a tail-ablation control.
    """
    sampled_steps = sample_device_sequence(
        trace_steps=trace_steps,
        labels=labels,
        n_operations=budget,
        rng=source_rng(base_seed, function_name, budget, run_idx, "sampled_device"),
    )
    truncated_steps = truncated_device_sequence(
        measured_steps,
        budget,
        source_rng(base_seed, function_name, budget, run_idx, "truncated_device"),
    )
    return {
        "sampled_device": sampled_steps,
        "gaussian": rms_matched_gaussian(
            sampled_steps,
            budget,
            source_rng(base_seed, function_name, budget, run_idx, "gaussian"),
        ),
        "uniform": rms_matched_uniform(
            sampled_steps,
            budget,
            source_rng(base_seed, function_name, budget, run_idx, "uniform"),
        ),
        "truncated_device": truncated_steps,
        "rms_truncated_device": scale_to_rms(truncated_steps, rms(sampled_steps)),
    }


def run_search(
    spec: FunctionSpec,
    step_sequence: np.ndarray,
    iterations: int,
    seed: int,
    accept_worse_prob: float = ACCEPT_WORSE_PROB,
) -> SearchResult:
    rng = np.random.default_rng(seed)
    pos_x = float(spec.start_pos[0])
    pos_y = float(spec.start_pos[1])
    best = spec.objective(pos_x, pos_y)
    best_values = np.empty(iterations + 1, dtype=float)
    accepted = np.empty(iterations, dtype=bool)
    clipped = np.empty(iterations, dtype=bool)
    best_values[0] = best

    for i in range(iterations):
        direction_x = rng.random()
        direction_y = rng.random()
        accept_random = rng.random()

        step = float(step_sequence[i % len(step_sequence)])
        raw_x = pos_x + (direction_x - 0.5) * 2.0 * step
        raw_y = pos_y + (direction_y - 0.5) * 2.0 * step
        candidate_x = min(max(raw_x, spec.search_lo), spec.search_hi)
        candidate_y = min(max(raw_y, spec.search_lo), spec.search_hi)
        f_pos = spec.objective(pos_x, pos_y)
        f_candidate = spec.objective(candidate_x, candidate_y)

        accept = f_candidate < f_pos or accept_random < accept_worse_prob
        if accept:
            pos_x = candidate_x
            pos_y = candidate_y
            f_pos = f_candidate

        best = min(best, f_pos)
        best_values[i + 1] = best
        accepted[i] = accept
        clipped[i] = raw_x != candidate_x or raw_y != candidate_y

    return SearchResult(best_values=best_values, accepted=accepted, clipped=clipped)


def first_hit_iteration(best_values: np.ndarray, threshold: float) -> int:
    hits = np.flatnonzero(best_values <= threshold)
    return int(hits[0]) if hits.size else -1


def threshold_key(threshold: float) -> str:
    return f"{threshold:g}"


def relative_improvement(function_name: str, final_best: np.ndarray | float) -> np.ndarray:
    start_value = FUNCTIONS[function_name].start_value
    values = np.asarray(final_best, dtype=float)
    return np.clip((start_value - values) / start_value, 0.0, 1.0)


def history_summary_from_histories(
    function_name: str,
    budget: int,
    histories: dict[str, list[np.ndarray]],
) -> pd.DataFrame:
    rows = []
    for source_name, source_histories in histories.items():
        h = np.vstack(source_histories)
        for iteration in range(h.shape[1]):
            values = h[:, iteration]
            rows.append(
                {
                    "function": function_name,
                    "budget": budget,
                    "source": source_name,
                    "iteration": iteration,
                    "median_best": float(np.median(values)),
                    "q25_best": float(np.quantile(values, 0.25)),
                    "q75_best": float(np.quantile(values, 0.75)),
                    "mean_best": float(np.mean(values)),
                }
            )
    return pd.DataFrame(rows)


def run_function_budget(
    spec: FunctionSpec,
    budget: int,
    n_runs: int,
    measured_steps: np.ndarray,
    trace_steps: pd.DataFrame,
    labels: np.ndarray,
    base_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    histories = {source_name: [] for source_name in SOURCES}
    run_rows = []

    for run_idx in range(n_runs):
        search_seed = base_seed + run_idx
        sequences = build_run_step_sequences(
            function_name=spec.name,
            budget=budget,
            run_idx=run_idx,
            measured_steps=measured_steps,
            trace_steps=trace_steps,
            labels=labels,
            base_seed=base_seed,
        )
        for source_name in SOURCES:
            steps = sequences[source_name]
            result = run_search(spec, steps, iterations=budget, seed=search_seed)
            histories[source_name].append(result.best_values)
            row = {
                "function": spec.name,
                "budget": budget,
                "source": source_name,
                "run": run_idx,
                "final_best": float(result.best_values[-1]),
                "min_best": float(np.min(result.best_values)),
                "relative_improvement": float(relative_improvement(spec.name, result.best_values[-1])),
                "accepted_fraction": float(np.mean(result.accepted)),
                "clipped_fraction": float(np.mean(result.clipped)),
                "step_rms": rms(steps),
                "step_median": float(np.median(steps)),
                "step_q90": float(np.quantile(steps, 0.90)),
                "step_q95": float(np.quantile(steps, 0.95)),
            }
            for threshold in spec.target_thresholds:
                hit_col = f"first_hit_le_{threshold_key(threshold)}"
                first_hit = first_hit_iteration(result.best_values, threshold)
                row[hit_col] = first_hit
                row[f"success_le_{threshold_key(threshold)}"] = bool(first_hit >= 0)
            run_rows.append(row)

    run_summary = pd.DataFrame(run_rows)
    fitvalue_curve = history_summary_from_histories(spec.name, budget, histories)
    return run_summary, fitvalue_curve


def summarize_budget_rows(run_summary: pd.DataFrame) -> pd.DataFrame:
    df = run_summary.copy()
    if "relative_improvement" not in df.columns:
        df["relative_improvement"] = [
            float(relative_improvement(function_name, final_best))
            for function_name, final_best in zip(df["function"], df["final_best"], strict=True)
        ]
    grouped = df.groupby(["function", "budget", "source"], sort=False)
    rows = []
    for (function_name, budget, source_name), g in grouped:
        rows.append(
            {
                "function": function_name,
                "display_name": FUNCTIONS[function_name].display_name,
                "budget": int(budget),
                "source": source_name,
                "source_label": SOURCE_LABELS[source_name],
                "n_runs": int(len(g)),
                "median_final_best": float(g["final_best"].median()),
                "q25_final_best": float(g["final_best"].quantile(0.25)),
                "q75_final_best": float(g["final_best"].quantile(0.75)),
                "median_relative_improvement": float(g["relative_improvement"].median()),
                "q25_relative_improvement": float(g["relative_improvement"].quantile(0.25)),
                "q75_relative_improvement": float(g["relative_improvement"].quantile(0.75)),
                "median_step_rms": float(g["step_rms"].median()) if "step_rms" in g else np.nan,
                "q25_step_rms": float(g["step_rms"].quantile(0.25)) if "step_rms" in g else np.nan,
                "q75_step_rms": float(g["step_rms"].quantile(0.75)) if "step_rms" in g else np.nan,
                "median_step_median": float(g["step_median"].median()) if "step_median" in g else np.nan,
                "median_step_q90": float(g["step_q90"].median()) if "step_q90" in g else np.nan,
                "median_step_q95": float(g["step_q95"].median()) if "step_q95" in g else np.nan,
            }
        )
    return pd.DataFrame(rows)


def summarize_success_rows(run_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    grouped = run_summary.groupby(["function", "budget", "source"], sort=False)
    for (function_name, budget, source_name), g in grouped:
        spec = FUNCTIONS[function_name]
        for threshold in spec.target_thresholds:
            hit_col = f"first_hit_le_{threshold_key(threshold)}"
            if hit_col not in g:
                continue
            hits = g[hit_col].astype(int)
            valid_hits = hits[hits >= 0]
            rows.append(
                {
                    "function": function_name,
                    "display_name": spec.display_name,
                    "budget": int(budget),
                    "source": source_name,
                    "source_label": SOURCE_LABELS[source_name],
                    "target_threshold": float(threshold),
                    "n_runs": int(len(g)),
                    "success_rate": float((hits >= 0).mean()),
                    "median_first_hit": float(valid_hits.median()) if len(valid_hits) else np.nan,
                    "q25_first_hit": float(valid_hits.quantile(0.25)) if len(valid_hits) else np.nan,
                    "q75_first_hit": float(valid_hits.quantile(0.75)) if len(valid_hits) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def plot_fitvalue_length(fitvalue_curve: pd.DataFrame, spec: FunctionSpec, budget: int, out_path: Path) -> None:
    fig, ax = plt.subplots(figsize=(4.4, 3.1))
    for source_name in SOURCES:
        g = fitvalue_curve[fitvalue_curve["source"] == source_name]
        ax.plot(
            g["iteration"],
            g["median_best"],
            label=SOURCE_LABELS[source_name],
            color=COLORS[source_name],
            linestyle=LINESTYLES[source_name],
            linewidth=1.4,
        )
        ax.fill_between(
            g["iteration"].to_numpy(),
            g["q25_best"].to_numpy(),
            g["q75_best"].to_numpy(),
            color=COLORS[source_name],
            alpha=0.07,
            linewidth=0,
        )
    ax.set_yscale("log")
    ax.set_xlabel("Iteration")
    ax.set_ylabel(f"Best {spec.display_name} value so far")
    ax.set_title(f"{spec.display_name}, budget = {budget}")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#E5E5E5", linewidth=0.6)
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=600)
    plt.close(fig)


def plot_budget_sensitivity_panel(summary: pd.DataFrame, function_name: str, out_path: Path) -> pd.DataFrame:
    panel_data = summary[summary["function"] == function_name].copy()
    spec = FUNCTIONS[function_name]
    fig, ax = plt.subplots(figsize=(4.4, 3.1))
    for source_name in SOURCES:
        g = panel_data[panel_data["source"] == source_name].sort_values("budget")
        x = g["budget"].to_numpy(dtype=float)
        y = g["median_relative_improvement"].to_numpy(dtype=float)
        lo = g["q25_relative_improvement"].to_numpy(dtype=float)
        hi = g["q75_relative_improvement"].to_numpy(dtype=float)
        ax.plot(
            x,
            y,
            marker="o",
            label=SOURCE_LABELS[source_name],
            color=COLORS[source_name],
            linestyle=LINESTYLES[source_name],
            linewidth=1.5,
            markersize=3.5,
        )
        ax.fill_between(x, lo, hi, color=COLORS[source_name], alpha=0.07, linewidth=0)
    ax.set_xscale("log")
    ax.set_xticks(sorted(panel_data["budget"].unique()))
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Function evaluations")
    ax.set_ylabel("Relative improvement")
    ax.set_title(f"{spec.display_name} budget sensitivity")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#E5E5E5", linewidth=0.6)
    ax.legend(frameon=False, fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=600)
    plt.close(fig)
    return panel_data


def success_panel_data_for_function(success_summary: pd.DataFrame, function_name: str) -> pd.DataFrame:
    if function_name not in FUNCTIONS:
        raise ValueError(f"unknown function: {function_name}")
    return success_summary[success_summary["function"] == function_name].copy()


def plot_success_rate_panel_for_function(
    success_summary: pd.DataFrame,
    function_name: str,
    out_path: Path,
) -> pd.DataFrame:
    panel_data = success_panel_data_for_function(success_summary, function_name)
    spec = FUNCTIONS[function_name]
    n_thresholds = len(spec.target_thresholds)
    n_cols = min(4, n_thresholds)
    n_rows = int(np.ceil(n_thresholds / n_cols))
    fig, axes = plt.subplots(
        n_rows,
        n_cols,
        figsize=(3.5 * n_cols, 2.9 * n_rows),
        sharey=True,
    )
    axes = np.asarray(axes).reshape(n_rows, n_cols)
    legend_handles = None
    legend_labels = None
    for threshold_idx, threshold in enumerate(spec.target_thresholds):
        row_idx = threshold_idx // n_cols
        col_idx = threshold_idx % n_cols
        ax = axes[row_idx, col_idx]
        subset = panel_data[np.isclose(panel_data["target_threshold"], threshold)]
        for source_name in SOURCES:
            g = subset[subset["source"] == source_name].sort_values("budget")
            ax.plot(
                g["budget"],
                g["success_rate"],
                marker="o",
                label=SOURCE_LABELS[source_name],
                color=COLORS[source_name],
                linestyle=LINESTYLES[source_name],
                linewidth=1.4,
                markersize=3.5,
            )
        if legend_handles is None:
            legend_handles, legend_labels = ax.get_legend_handles_labels()
        ax.set_xscale("log")
        ax.set_xticks(sorted(subset["budget"].unique()))
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_title(f"target <= {threshold:g}")
        ax.set_xlabel("Function evaluations")
        if col_idx == 0:
            ax.set_ylabel("Success rate")
        ax.set_ylim(0, 1.02)
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", color="#E5E5E5", linewidth=0.6)
    for empty_idx in range(n_thresholds, n_rows * n_cols):
        row_idx = empty_idx // n_cols
        col_idx = empty_idx % n_cols
        axes[row_idx, col_idx].axis("off")
    fig.suptitle(f"{spec.display_name} success rate", y=0.98)
    if legend_handles is not None:
        fig.legend(
            legend_handles,
            legend_labels,
            frameon=False,
            fontsize=7,
            loc="lower center",
            ncol=len(SOURCES),
        )
        fig.subplots_adjust(bottom=0.14)
    fig.tight_layout(rect=(0, 0.08, 1, 0.94))
    fig.savefig(out_path, dpi=600)
    plt.close(fig)
    return panel_data.copy()


def parse_budgets(value: str) -> list[int]:
    budgets = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not budgets or any(b <= 0 for b in budgets):
        raise argparse.ArgumentTypeError("budgets must be a comma-separated list of positive integers")
    return budgets


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run budget sensitivity benchmark and save PNG/CSV outputs.")
    parser.add_argument("--n-runs", type=int, default=DEFAULT_N_RUNS)
    parser.add_argument("--budgets", type=parse_budgets, default=DEFAULT_BUDGETS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--base-seed", type=int, default=BASE_SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    measured_steps, trace_steps, labels = load_step_inputs()
    input_summary = pd.DataFrame(
        [
            {"name": "n_measured_steps", "value": measured_steps.size},
            {"name": "measured_rms", "value": rms(measured_steps)},
            {"name": "measured_median", "value": float(np.median(measured_steps))},
            {"name": "measured_q90", "value": float(np.quantile(measured_steps, 0.90))},
            {"name": "measured_q95", "value": float(np.quantile(measured_steps, 0.95))},
            {"name": "truncate_top_fraction", "value": TRUNCATE_TOP_FRACTION},
            {"name": "gaussian_uniform_rms_reference", "value": "per-run sampled_device"},
            {"name": "truncated_device_rescaled", "value": "False"},
            {"name": "rms_truncated_device_rms_reference", "value": "per-run sampled_device"},
            {"name": "n_runs", "value": args.n_runs},
            {"name": "budgets", "value": ",".join(str(b) for b in args.budgets)},
            {
                "name": "target_thresholds",
                "value": ";".join(
                    f"{name}:{','.join(threshold_key(t) for t in spec.target_thresholds)}"
                    for name, spec in FUNCTIONS.items()
                ),
            },
        ]
    )
    input_summary.to_csv(output_dir / "budget_sensitivity_input_summary.csv", index=False)

    all_run_summaries = []
    all_curve_summaries = []
    for function_name in FUNCTION_ORDER:
        spec = FUNCTIONS[function_name]
        for budget in args.budgets:
            print(f"Running {spec.display_name}, budget={budget}, n_runs={args.n_runs}")
            run_summary, fitvalue_curve = run_function_budget(
                spec=spec,
                budget=budget,
                n_runs=args.n_runs,
                measured_steps=measured_steps,
                trace_steps=trace_steps,
                labels=labels,
                base_seed=args.base_seed,
            )
            run_summary.to_csv(output_dir / f"{function_name}_budget_{budget}_run_summary.csv", index=False)
            fitvalue_curve.to_csv(output_dir / f"{function_name}_budget_{budget}_fitvalue_length.csv", index=False)
            plot_fitvalue_length(
                fitvalue_curve,
                spec,
                budget,
                output_dir / f"{function_name}_budget_{budget}_fitvalue_length.png",
            )
            all_run_summaries.append(run_summary)
            all_curve_summaries.append(fitvalue_curve)

    all_runs = pd.concat(all_run_summaries, ignore_index=True)
    all_runs.to_csv(output_dir / "budget_sensitivity_all_run_summary.csv", index=False)
    all_curves = pd.concat(all_curve_summaries, ignore_index=True)
    all_curves.to_csv(output_dir / "budget_sensitivity_all_fitvalue_length.csv", index=False)

    summary = summarize_budget_rows(all_runs)
    summary.to_csv(output_dir / "budget_sensitivity_summary.csv", index=False)
    success_summary = summarize_success_rows(all_runs)
    success_summary.to_csv(output_dir / "budget_sensitivity_success_rate_summary.csv", index=False)

    for idx, function_name in enumerate(FUNCTION_ORDER):
        letter = chr(ord("a") + idx)
        panel = plot_budget_sensitivity_panel(
            summary,
            function_name,
            output_dir / f"panel_{letter}_{function_name}_budget_sensitivity.png",
        )
        panel.to_csv(output_dir / f"panel_{letter}_{function_name}_budget_sensitivity.csv", index=False)

    success_letter = chr(ord("a") + len(FUNCTION_ORDER))
    for function_name in FUNCTION_ORDER:
        panel_success = plot_success_rate_panel_for_function(
            success_summary,
            function_name,
            output_dir / f"panel_{success_letter}_{function_name}_success_rate_multi_threshold.png",
        )
        panel_success.to_csv(
            output_dir / f"panel_{success_letter}_{function_name}_success_rate_multi_threshold.csv",
            index=False,
        )

    print(f"Wrote outputs to {output_dir.resolve()}")


if __name__ == "__main__":
    main()
