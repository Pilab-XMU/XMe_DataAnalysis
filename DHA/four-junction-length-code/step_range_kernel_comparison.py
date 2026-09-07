"""Compare four empirical staircase-range response-step sampling kernels."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
matplotlib.rcParams["font.family"] = "Arial"
matplotlib.rcParams["mathtext.fontset"] = "dejavusans"
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import budget_sensitivity_demo as base


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "step_range_kernel_comparison_outputs"
STEP_RANGES = base.STEP_RANGES
SOURCE_LABELS = {step_range: step_range for step_range in STEP_RANGES}
COLORS = {
    "0_05": "#0072B2",
    "05_10": "#E69F00",
    "10_15": "#009E73",
    "15_20": "#CC79A7",
}
LINESTYLES = {
    "0_05": "-",
    "05_10": "--",
    "10_15": "-.",
    "15_20": ":",
}


@dataclass(frozen=True)
class KernelData:
    step_range: str
    trace_steps: pd.DataFrame
    labels: np.ndarray
    measured_steps: np.ndarray
    measured_sequence: pd.DataFrame


def _require_columns(df: pd.DataFrame, required: set[str], path: Path) -> None:
    missing = sorted(required - set(df.columns))
    if missing:
        raise ValueError(f"{path} is missing required columns: {', '.join(missing)}")


def center_crop(values: np.ndarray, length: int) -> np.ndarray:
    if length <= 0 or values.size < length:
        raise ValueError("invalid center-crop length")
    start = (values.size - length) // 2
    return values[start : start + length]


def extract_response_steps_from_class(
    class_id: int,
    class_name: str,
    csv_path: Path,
) -> pd.DataFrame:
    """Extract median(abs(R2-R1)) for every raw trace in one class file."""
    df = pd.read_csv(csv_path, usecols=["x", "log"])
    trace_ids = (df["x"].diff().fillna(0) < 0).cumsum()
    df = df.assign(trace_id=trace_ids.to_numpy())
    rows = []
    for trace_id, trace in df.groupby("trace_id", sort=True):
        r1 = trace.loc[(trace["x"] >= 200) & (trace["x"] < 300), "log"].to_numpy(dtype=float)
        r2 = trace.loc[(trace["x"] >= 400) & (trace["x"] < 500), "log"].to_numpy(dtype=float)
        aligned_length = min(r1.size, r2.size)
        if aligned_length == 0:
            raise ValueError(f"trace {int(trace_id)} in {csv_path.name} has no R1 or R2 samples")
        step = float(
            np.median(
                np.abs(
                    center_crop(r2, aligned_length)
                    - center_crop(r1, aligned_length)
                )
            )
        )
        if not np.isfinite(step):
            raise ValueError(f"trace {int(trace_id)} in {csv_path.name} produced a non-finite step")
        rows.append(
            {
                "class_id": class_id,
                "class_name": class_name,
                "trace_id_in_class": int(trace_id),
                "aligned_length": int(aligned_length),
                "sE": step,
            }
        )
    return pd.DataFrame(rows)


def load_raw_serial_labels(path: Path) -> np.ndarray:
    df = pd.read_csv(path)
    if df.shape[1] < 1:
        raise ValueError(f"{path} has no class-label column")
    labels = df.iloc[:, -1].astype(int).to_numpy()
    unknown = sorted(set(labels) - set(base.CLASS_SPECS))
    if unknown:
        raise ValueError(f"{path} contains unknown class labels: {unknown}")
    return labels


def reconstruct_measured_sequence(trace_steps: pd.DataFrame, labels: np.ndarray) -> pd.DataFrame:
    """Consume each class's extracted traces in serial occurrence order."""
    for class_id in base.CLASS_SPECS:
        serial_count = int(np.sum(labels == class_id))
        trace_count = int(np.sum(trace_steps["class_id"].to_numpy(dtype=int) == class_id))
        if serial_count != trace_count:
            raise ValueError(
                f"class {class_id} count mismatch: serial={serial_count}, traces={trace_count}"
            )
    queues = {
        class_id: trace_steps.loc[trace_steps["class_id"] == class_id]
        .sort_values("trace_id_in_class")
        .reset_index(drop=True)
        for class_id in base.CLASS_SPECS
    }
    cursors = {class_id: 0 for class_id in base.CLASS_SPECS}
    rows = []
    for operation_index, class_id_value in enumerate(labels):
        class_id = int(class_id_value)
        trace = queues[class_id].iloc[cursors[class_id]]
        cursors[class_id] += 1
        rows.append(
            {
                "operation_index": operation_index,
                "cycle_index": operation_index,
                "class_id": class_id,
                "class_name": base.CLASS_SPECS[class_id]["name"],
                "operation": "E",
                "step": float(trace["sE"]),
                "is_memristive_class": bool(base.CLASS_SPECS[class_id]["is_memristive"]),
            }
        )
    return pd.DataFrame(rows)


def build_kernel_from_raw(data_dir: Path, step_range: str) -> KernelData:
    """Build one sampling kernel directly from raw class and serial CSVs."""
    if step_range not in STEP_RANGES:
        raise ValueError(f"unknown step range: {step_range}")
    labels = load_raw_serial_labels(data_dir / f"serial{step_range}.csv")
    parts = []
    for class_id, class_spec in base.CLASS_SPECS.items():
        raw_path = data_dir / f"{class_spec['file_stem']}{step_range}.csv"
        required_count = int(np.sum(labels == class_id))
        if not raw_path.exists():
            if required_count:
                raise FileNotFoundError(
                    f"missing {raw_path.name}: serial requires {required_count} class {class_id} traces"
                )
            continue
        parts.append(
            extract_response_steps_from_class(
                class_id,
                str(class_spec["name"]),
                raw_path,
            )
        )
    columns = ["class_id", "class_name", "trace_id_in_class", "aligned_length", "sE"]
    trace_steps = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=columns)
    measured_sequence = reconstruct_measured_sequence(trace_steps, labels)
    measured_steps = measured_sequence["step"].to_numpy(dtype=float)
    return KernelData(step_range, trace_steps, labels, measured_steps, measured_sequence)


def build_kernels_from_raw(data_dir: Path) -> dict[str, KernelData]:
    return {step_range: build_kernel_from_raw(data_dir, step_range) for step_range in STEP_RANGES}


def write_derived_kernels(kernels: dict[str, KernelData], output_dir: Path) -> None:
    """Save locally derived kernels in the same layout accepted by load_kernels."""
    for step_range, kernel in kernels.items():
        range_dir = output_dir / step_range
        range_dir.mkdir(parents=True, exist_ok=True)
        trace_steps = kernel.trace_steps.copy()
        trace_steps["step_range"] = step_range
        columns = ["step_range"] + [column for column in trace_steps if column != "step_range"]
        trace_steps[columns].to_csv(range_dir / "response_steps_by_trace.csv", index=False)

        sequence = kernel.measured_sequence.copy()
        sequence["step_range"] = step_range
        columns = ["step_range"] + [column for column in sequence if column != "step_range"]
        sequence[columns].to_csv(range_dir / "measured_operation_sequence.csv", index=False)


def load_kernel(input_dir: Path, step_range: str) -> KernelData:
    """Load and validate one range's previously derived response-step files."""
    if step_range not in STEP_RANGES:
        raise ValueError(f"unknown step range: {step_range}")
    range_dir = input_dir / step_range
    trace_path = range_dir / "response_steps_by_trace.csv"
    sequence_path = range_dir / "measured_operation_sequence.csv"
    trace_steps = pd.read_csv(trace_path)
    sequence = pd.read_csv(sequence_path)
    _require_columns(trace_steps, {"class_id", "sE"}, trace_path)
    _require_columns(sequence, {"class_id", "step"}, sequence_path)

    for df, path in ((trace_steps, trace_path), (sequence, sequence_path)):
        if "step_range" in df and set(df["step_range"].astype(str)) != {step_range}:
            raise ValueError(f"{path} contains data outside step range {step_range}")

    trace_steps = trace_steps.copy()
    trace_steps["class_id"] = trace_steps["class_id"].astype(int)
    trace_steps["sE"] = trace_steps["sE"].astype(float)
    labels = sequence["class_id"].astype(int).to_numpy()
    measured_steps = sequence["step"].astype(float).to_numpy()

    known_classes = set(base.CLASS_SPECS)
    unknown = sorted((set(trace_steps["class_id"]) | set(labels)) - known_classes)
    if unknown:
        raise ValueError(f"{step_range} contains unknown class labels: {unknown}")
    if len(trace_steps) == 0 or len(labels) == 0:
        raise ValueError(f"{step_range} kernel is empty")
    if not np.isfinite(trace_steps["sE"]).all() or not np.isfinite(measured_steps).all():
        raise ValueError(f"{step_range} contains non-finite steps")
    if (trace_steps["sE"] < 0).any() or (measured_steps < 0).any():
        raise ValueError(f"{step_range} contains negative steps")

    trace_counts = trace_steps["class_id"].value_counts().sort_index().to_dict()
    serial_counts = pd.Series(labels).value_counts().sort_index().to_dict()
    if trace_counts != serial_counts:
        raise ValueError(
            f"{step_range} class-count mismatch: traces={trace_counts}, serial={serial_counts}"
        )
    return KernelData(step_range, trace_steps, labels, measured_steps, sequence)


def load_kernels(input_dir: Path) -> dict[str, KernelData]:
    return {step_range: load_kernel(input_dir, step_range) for step_range in STEP_RANGES}


def kernel_rng(
    base_seed: int,
    function_name: str,
    budget: int,
    run_idx: int,
    step_range: str,
) -> np.random.Generator:
    function_idx = base.FUNCTION_ORDER.index(function_name)
    range_idx = STEP_RANGES.index(step_range)
    seed_sequence = np.random.SeedSequence([base_seed, function_idx, budget, run_idx, range_idx])
    return np.random.default_rng(seed_sequence)


def run_function_budget(
    spec: base.FunctionSpec,
    budget: int,
    n_runs: int,
    kernels: dict[str, KernelData],
    base_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Run one objective/budget with paired search randomness across kernels."""
    if tuple(kernels) != STEP_RANGES:
        raise ValueError(f"kernels must be ordered as {STEP_RANGES}")
    histories = {step_range: [] for step_range in STEP_RANGES}
    run_rows = []

    for run_idx in range(n_runs):
        search_seed = base_seed + run_idx
        for step_range, kernel in kernels.items():
            steps = base.sample_device_sequence(
                trace_steps=kernel.trace_steps,
                labels=kernel.labels,
                n_operations=budget,
                rng=kernel_rng(base_seed, spec.name, budget, run_idx, step_range),
            )
            result = base.run_search(spec, steps, iterations=budget, seed=search_seed)
            histories[step_range].append(result.best_values)
            row = {
                "function": spec.name,
                "budget": budget,
                "source": step_range,
                "source_label": SOURCE_LABELS[step_range],
                "run": run_idx,
                "final_best": float(result.best_values[-1]),
                "min_best": float(np.min(result.best_values)),
                "relative_improvement": float(base.relative_improvement(spec.name, result.best_values[-1])),
                "accepted_fraction": float(np.mean(result.accepted)),
                "clipped_fraction": float(np.mean(result.clipped)),
                "step_rms": base.rms(steps),
                "step_median": float(np.median(steps)),
                "step_q90": float(np.quantile(steps, 0.90)),
                "step_q95": float(np.quantile(steps, 0.95)),
            }
            for threshold in spec.target_thresholds:
                key = base.threshold_key(threshold)
                first_hit = base.first_hit_iteration(result.best_values, threshold)
                row[f"first_hit_le_{key}"] = first_hit
                row[f"success_le_{key}"] = bool(first_hit >= 0)
            run_rows.append(row)

    run_summary = pd.DataFrame(run_rows)
    curve = base.history_summary_from_histories(spec.name, budget, histories)
    curve["source_label"] = curve["source"].map(SOURCE_LABELS)
    return run_summary, curve


def summarize_budget_rows(run_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (function_name, budget, source), group in run_summary.groupby(
        ["function", "budget", "source"], sort=False
    ):
        rows.append(
            {
                "function": function_name,
                "display_name": base.FUNCTIONS[function_name].display_name,
                "budget": int(budget),
                "source": source,
                "source_label": SOURCE_LABELS[source],
                "n_runs": int(len(group)),
                "median_final_best": float(group["final_best"].median()),
                "q25_final_best": float(group["final_best"].quantile(0.25)),
                "q75_final_best": float(group["final_best"].quantile(0.75)),
                "median_relative_improvement": float(group["relative_improvement"].median()),
                "q25_relative_improvement": float(group["relative_improvement"].quantile(0.25)),
                "q75_relative_improvement": float(group["relative_improvement"].quantile(0.75)),
                "median_step_rms": float(group["step_rms"].median()),
                "median_step_median": float(group["step_median"].median()),
                "median_step_q90": float(group["step_q90"].median()),
                "median_step_q95": float(group["step_q95"].median()),
            }
        )
    return pd.DataFrame(rows)


def summarize_success_rows(run_summary: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (function_name, budget, source), group in run_summary.groupby(
        ["function", "budget", "source"], sort=False
    ):
        spec = base.FUNCTIONS[function_name]
        for threshold in spec.target_thresholds:
            hit_column = f"first_hit_le_{base.threshold_key(threshold)}"
            hits = group[hit_column].astype(int)
            valid_hits = hits[hits >= 0]
            rows.append(
                {
                    "function": function_name,
                    "display_name": spec.display_name,
                    "budget": int(budget),
                    "source": source,
                    "source_label": SOURCE_LABELS[source],
                    "target_threshold": float(threshold),
                    "n_runs": int(len(group)),
                    "success_rate": float((hits >= 0).mean()),
                    "median_first_hit": float(valid_hits.median()) if len(valid_hits) else np.nan,
                    "q25_first_hit": float(valid_hits.quantile(0.25)) if len(valid_hits) else np.nan,
                    "q75_first_hit": float(valid_hits.quantile(0.75)) if len(valid_hits) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def plot_fitvalue_length(
    curve: pd.DataFrame,
    spec: base.FunctionSpec,
    budget: int,
    out_path: Path,
) -> None:
    fig, ax = plt.subplots(figsize=(4.4, 3.1))
    for step_range in STEP_RANGES:
        group = curve[curve["source"] == step_range]
        ax.plot(
            group["iteration"],
            group["median_best"],
            label=SOURCE_LABELS[step_range],
            color=COLORS[step_range],
            linestyle=LINESTYLES[step_range],
            linewidth=1.4,
        )
        ax.fill_between(
            group["iteration"].to_numpy(),
            group["q25_best"].to_numpy(),
            group["q75_best"].to_numpy(),
            color=COLORS[step_range],
            alpha=0.07,
            linewidth=0,
        )
    ax.set_yscale("log")
    ax.set_xlabel("Iteration")
    ax.set_ylabel(f"Best {spec.display_name} value so far")
    ax.set_title(f"{spec.display_name}, budget = {budget}")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#E5E5E5", linewidth=0.6)
    ax.legend(title="Step range", frameon=False, fontsize=7, title_fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=600)
    plt.close(fig)


def plot_budget_sensitivity_panel(
    summary: pd.DataFrame,
    function_name: str,
    out_path: Path,
) -> pd.DataFrame:
    panel_data = summary[summary["function"] == function_name].copy()
    spec = base.FUNCTIONS[function_name]
    fig, ax = plt.subplots(figsize=(4.4, 3.1))
    for step_range in STEP_RANGES:
        group = panel_data[panel_data["source"] == step_range].sort_values("budget")
        x = group["budget"].to_numpy(dtype=float)
        y = group["median_relative_improvement"].to_numpy(dtype=float)
        low = group["q25_relative_improvement"].to_numpy(dtype=float)
        high = group["q75_relative_improvement"].to_numpy(dtype=float)
        ax.plot(
            x,
            y,
            marker="o",
            label=SOURCE_LABELS[step_range],
            color=COLORS[step_range],
            linestyle=LINESTYLES[step_range],
            linewidth=1.5,
            markersize=3.5,
        )
        ax.fill_between(x, low, high, color=COLORS[step_range], alpha=0.07, linewidth=0)
    ax.set_xscale("log")
    ax.set_xticks(sorted(panel_data["budget"].unique()))
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_ylim(0, 1.02)
    ax.set_xlabel("Function evaluations")
    ax.set_ylabel("Relative improvement")
    ax.set_title(f"{spec.display_name} budget sensitivity")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#E5E5E5", linewidth=0.6)
    ax.legend(title="Step range", frameon=False, fontsize=7, title_fontsize=7)
    fig.tight_layout()
    fig.savefig(out_path, dpi=600)
    plt.close(fig)
    return panel_data


def plot_success_rate_panel(
    success_summary: pd.DataFrame,
    function_name: str,
    out_path: Path,
) -> pd.DataFrame:
    panel_data = success_summary[success_summary["function"] == function_name].copy()
    spec = base.FUNCTIONS[function_name]
    n_thresholds = len(spec.target_thresholds)
    n_cols = min(4, n_thresholds)
    n_rows = int(np.ceil(n_thresholds / n_cols))
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3.5 * n_cols, 2.9 * n_rows), sharey=True)
    axes = np.asarray(axes).reshape(n_rows, n_cols)
    legend_handles = None
    legend_labels = None
    for threshold_idx, threshold in enumerate(spec.target_thresholds):
        row_idx = threshold_idx // n_cols
        col_idx = threshold_idx % n_cols
        ax = axes[row_idx, col_idx]
        subset = panel_data[np.isclose(panel_data["target_threshold"], threshold)]
        for step_range in STEP_RANGES:
            group = subset[subset["source"] == step_range].sort_values("budget")
            ax.plot(
                group["budget"],
                group["success_rate"],
                marker="o",
                label=SOURCE_LABELS[step_range],
                color=COLORS[step_range],
                linestyle=LINESTYLES[step_range],
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
        axes[empty_idx // n_cols, empty_idx % n_cols].axis("off")
    fig.suptitle(f"{spec.display_name} success rate", y=0.98)
    if legend_handles is not None:
        fig.legend(
            legend_handles,
            legend_labels,
            title="Step range",
            frameon=False,
            fontsize=7,
            title_fontsize=7,
            loc="lower center",
            ncol=4,
        )
        fig.subplots_adjust(bottom=0.14)
    fig.tight_layout(rect=(0, 0.08, 1, 0.94))
    fig.savefig(out_path, dpi=600)
    plt.close(fig)
    return panel_data


def build_input_summary(kernels: dict[str, KernelData]) -> pd.DataFrame:
    rows = []
    for step_range, kernel in kernels.items():
        values = kernel.trace_steps["sE"].to_numpy(dtype=float)
        rows.extend(
            [
                {"step_range": step_range, "name": "n_steps", "value": len(values)},
                {"step_range": step_range, "name": "step_rms", "value": base.rms(values)},
                {"step_range": step_range, "name": "step_median", "value": float(np.median(values))},
                {"step_range": step_range, "name": "step_q90", "value": float(np.quantile(values, 0.90))},
                {"step_range": step_range, "name": "step_q95", "value": float(np.quantile(values, 0.95))},
            ]
        )
        for class_id in base.CLASS_SPECS:
            rows.append(
                {
                    "step_range": step_range,
                    "name": f"class_{class_id}_count",
                    "value": int(np.sum(kernel.labels == class_id)),
                }
            )
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare four measured staircase-range response-step kernels."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=BASE_DIR,
        help="Directory containing raw data*.csv and serial*.csv files (default: script directory).",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=None,
        help="Optional derived-step directory; when supplied, raw extraction is skipped.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--n-runs", type=int, default=base.DEFAULT_N_RUNS)
    parser.add_argument("--budgets", type=base.parse_budgets, default=base.DEFAULT_BUDGETS)
    parser.add_argument("--base-seed", type=int, default=base.BASE_SEED)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.n_runs <= 0:
        raise ValueError("n-runs must be positive")
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.input_dir is None:
        print(f"Deriving four response-step kernels from raw data in {args.data_dir.resolve()}")
        kernels = build_kernels_from_raw(args.data_dir)
        derived_dir = output_dir / "derived_steps"
        write_derived_kernels(kernels, derived_dir)
        input_mode = "raw_data"
        input_location = args.data_dir.resolve()
    else:
        print(f"Loading four response-step kernels from {args.input_dir.resolve()}")
        kernels = load_kernels(args.input_dir)
        input_mode = "derived_steps"
        input_location = args.input_dir.resolve()
    input_summary = build_input_summary(kernels)
    input_summary["input_mode"] = input_mode
    input_summary["input_location"] = str(input_location)
    input_summary.to_csv(output_dir / "kernel_input_summary.csv", index=False)

    all_run_summaries = []
    all_curves = []
    for function_name in base.FUNCTION_ORDER:
        spec = base.FUNCTIONS[function_name]
        for budget in args.budgets:
            print(
                f"Running four step-range kernels: {spec.display_name}, "
                f"budget={budget}, n_runs={args.n_runs}"
            )
            run_summary, curve = run_function_budget(
                spec=spec,
                budget=budget,
                n_runs=args.n_runs,
                kernels=kernels,
                base_seed=args.base_seed,
            )
            run_summary.to_csv(
                output_dir / f"{function_name}_budget_{budget}_run_summary.csv",
                index=False,
            )
            curve.to_csv(
                output_dir / f"{function_name}_budget_{budget}_fitvalue_length.csv",
                index=False,
            )
            plot_fitvalue_length(
                curve,
                spec,
                budget,
                output_dir / f"{function_name}_budget_{budget}_fitvalue_length.png",
            )
            all_run_summaries.append(run_summary)
            all_curves.append(curve)

    all_runs = pd.concat(all_run_summaries, ignore_index=True)
    all_curve_rows = pd.concat(all_curves, ignore_index=True)
    all_runs.to_csv(output_dir / "step_range_kernel_all_run_summary.csv", index=False)
    all_curve_rows.to_csv(output_dir / "step_range_kernel_all_fitvalue_length.csv", index=False)
    summary = summarize_budget_rows(all_runs)
    summary.to_csv(output_dir / "step_range_kernel_summary.csv", index=False)
    success_summary = summarize_success_rows(all_runs)
    success_summary.to_csv(output_dir / "step_range_kernel_success_rate_summary.csv", index=False)

    for idx, function_name in enumerate(base.FUNCTION_ORDER):
        letter = chr(ord("a") + idx)
        panel = plot_budget_sensitivity_panel(
            summary,
            function_name,
            output_dir / f"panel_{letter}_{function_name}_step_range_budget_sensitivity.png",
        )
        panel.to_csv(
            output_dir / f"panel_{letter}_{function_name}_step_range_budget_sensitivity.csv",
            index=False,
        )
        success_panel = plot_success_rate_panel(
            success_summary,
            function_name,
            output_dir / f"panel_{letter}_{function_name}_step_range_success_rate.png",
        )
        success_panel.to_csv(
            output_dir / f"panel_{letter}_{function_name}_step_range_success_rate.csv",
            index=False,
        )

    print(f"Wrote outputs to {output_dir.resolve()}")


if __name__ == "__main__":
    main()
