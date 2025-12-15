#!/usr/bin/env python3
"""
Synthetic demand planning dataset generator.

This utility creates a CSV file that mirrors the structure expected by the demand
planning workflow:

    date,sku,demand_units,on_hand,lead_time_days,product_name

The generation logic introduces SKU-level trends, weekly/annual seasonality,
random noise, and infrequent promotional spikes so that the resulting dataset can
exercise validation, anomaly detection, and aggregation paths during demos.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Tuple


@dataclass
class SkuProfile:
    sku: str
    product_name: str
    base_demand: float
    lead_time_days: int
    seasonality: float
    trend_pct: float
    promo_lift_range: Tuple[float, float]


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}'; expected YYYY-MM-DD") from exc


def iter_dates(start: date, end: date) -> Iterable[date]:
    current = start
    step = timedelta(days=1)
    while current <= end:
        yield current
        current += step


def build_sku_profiles(args: argparse.Namespace) -> List[SkuProfile]:
    profiles = []
    for index in range(args.sku_count):
        sku_suffix = index + 1
        sku = f"{args.sku_prefix}{sku_suffix:03d}"
        product_name = f"{args.product_name_prefix} {sku_suffix:03d}"
        base_demand = random.uniform(args.base_demand_min, args.base_demand_max)
        lead_time_days = random.randint(args.lead_time_min, args.lead_time_max)
        seasonality = random.uniform(0.05, args.seasonality_strength)
        trend_pct = random.uniform(-args.trend_pct, args.trend_pct)
        promo_lift_range = (
            args.promo_lift_min,
            random.uniform(args.promo_lift_min, args.promo_lift_max),
        )
        profiles.append(
            SkuProfile(
                sku=sku,
                product_name=product_name,
                base_demand=base_demand,
                lead_time_days=lead_time_days,
                seasonality=seasonality,
                trend_pct=trend_pct,
                promo_lift_range=promo_lift_range,
            )
        )
    return profiles


def generate_rows(
    profiles: Iterable[SkuProfile],
    dates: List[date],
    args: argparse.Namespace,
) -> Iterable[Tuple[str, str, int, int, int, str]]:
    total_periods = len(dates) - 1 if len(dates) > 1 else 1

    for day_index, current_date in enumerate(dates):
        progress = day_index / total_periods if total_periods else 0.0
        week_component = math.sin(2 * math.pi * (current_date.weekday() / 7.0))
        year_component = math.sin(2 * math.pi * (current_date.timetuple().tm_yday / 365.0))

        for profile in profiles:
            seasonal_influence = profile.seasonality * (0.6 * week_component + 0.4 * year_component)
            seasonal_factor = max(0.2, 1.0 + seasonal_influence)

            trend_factor = 1.0 + profile.trend_pct * progress

            noise_factor = 1.0 + random.gauss(0, args.demand_noise_pct)
            noise_factor = max(0.1, noise_factor)

            promo_multiplier = 1.0
            if random.random() < args.promo_probability:
                lift = random.uniform(*profile.promo_lift_range)
                promo_multiplier += lift

            demand_value = profile.base_demand * seasonal_factor * trend_factor
            demand_value *= promo_multiplier
            demand_value *= noise_factor

            demand_units = max(0, int(round(demand_value)))

            if args.zero_demand_probability and random.random() < args.zero_demand_probability:
                demand_units = 0

            coverage_days = profile.lead_time_days + args.safety_stock_days
            expected_daily = profile.base_demand * seasonal_factor
            base_on_hand = coverage_days * expected_daily
            inventory_jitter = 1.0 + random.gauss(0, args.inventory_jitter_pct)
            inventory_jitter = max(0.5, inventory_jitter)
            on_hand = max(demand_units, int(round(base_on_hand * inventory_jitter)))

            yield (
                current_date.isoformat(),
                profile.sku,
                demand_units,
                on_hand,
                profile.lead_time_days,
                profile.product_name,
            )


def ensure_output_directory(path: Path) -> None:
    os.makedirs(path.parent, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a synthetic demand planning CSV for demos."
    )
    parser.add_argument(
        "--start-date",
        type=parse_date,
        default=parse_date("2023-01-01"),
        help="Inclusive start date for the generated series (default: 2023-01-01).",
    )
    parser.add_argument(
        "--end-date",
        type=parse_date,
        default=parse_date("2024-12-31"),
        help="Inclusive end date for the generated series (default: 2024-12-31).",
    )
    parser.add_argument(
        "--sku-count",
        type=int,
        default=25,
        help="Number of unique SKUs to generate (default: 25).",
    )
    parser.add_argument(
        "--sku-prefix",
        default="SKU-",
        help="Prefix for generated SKUs (default: SKU-).",
    )
    parser.add_argument(
        "--product-name-prefix",
        default="Synthetic Product",
        help="Prefix for generated product names (default: Synthetic Product).",
    )
    parser.add_argument(
        "--base-demand-min",
        type=float,
        default=60.0,
        help="Minimum average daily demand per SKU (default: 60).",
    )
    parser.add_argument(
        "--base-demand-max",
        type=float,
        default=200.0,
        help="Maximum average daily demand per SKU (default: 200).",
    )
    parser.add_argument(
        "--lead-time-min",
        type=int,
        default=5,
        help="Minimum lead time in days (default: 5).",
    )
    parser.add_argument(
        "--lead-time-max",
        type=int,
        default=18,
        help="Maximum lead time in days (default: 18).",
    )
    parser.add_argument(
        "--safety-stock-days",
        type=int,
        default=5,
        help="Extra days of coverage to multiply on-hand inventory (default: 5).",
    )
    parser.add_argument(
        "--seasonality-strength",
        type=float,
        default=0.20,
        help="Upper bound for SKU seasonality amplitude (default: 0.20).",
    )
    parser.add_argument(
        "--trend-pct",
        type=float,
        default=0.10,
        help="Maximum absolute total trend over the scripted period (default: 0.10).",
    )
    parser.add_argument(
        "--demand-noise-pct",
        type=float,
        default=0.08,
        help="Standard deviation for Gaussian demand noise as a fraction (default: 0.08).",
    )
    parser.add_argument(
        "--inventory-jitter-pct",
        type=float,
        default=0.03,
        help="Standard deviation for inventory jitter as a fraction (default: 0.03).",
    )
    parser.add_argument(
        "--promo-probability",
        type=float,
        default=0.025,
        help="Probability of a promotional lift on any day/SKU (default: 0.025).",
    )
    parser.add_argument(
        "--promo-lift-min",
        type=float,
        default=0.10,
        help="Minimum promotional lift multiplier (default: 0.10).",
    )
    parser.add_argument(
        "--promo-lift-max",
        type=float,
        default=0.40,
        help="Maximum promotional lift multiplier (default: 0.40).",
    )
    parser.add_argument(
        "--zero-demand-probability",
        type=float,
        default=0.0,
        help="Probability that a given day/SKU has zero demand (default: 0.0).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=1337,
        help="Random seed for reproducibility (default: 1337).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("sample_data/demand_planning_synthetic.csv"),
        help="Destination CSV file path (default: sample_data/demand_planning_synthetic.csv).",
    )
    args = parser.parse_args()

    if args.end_date < args.start_date:
        raise SystemExit("end-date must be on or after start-date.")

    if args.sku_count < 1:
        raise SystemExit("sku-count must be at least 1.")

    if args.base_demand_min <= 0 or args.base_demand_max <= 0:
        raise SystemExit("base demand bounds must be positive.")

    if args.base_demand_min >= args.base_demand_max:
        raise SystemExit("base-demand-min must be less than base-demand-max.")

    if args.lead_time_min <= 0 or args.lead_time_max <= 0:
        raise SystemExit("lead times must be positive.")

    if args.lead_time_min > args.lead_time_max:
        raise SystemExit("lead-time-min cannot exceed lead-time-max.")

    if not 0 <= args.promo_probability <= 1:
        raise SystemExit("promo-probability must be between 0 and 1.")

    if args.promo_lift_min < 0 or args.promo_lift_max < 0:
        raise SystemExit("promo lift bounds must be non-negative.")

    if args.promo_lift_min > args.promo_lift_max:
        raise SystemExit("promo-lift-min cannot exceed promo-lift-max.")

    if not 0.0 <= args.zero_demand_probability <= 1.0:
        raise SystemExit("zero-demand-probability must be between 0 and 1.")

    random.seed(args.seed)
    return args


def main() -> None:
    args = parse_args()

    date_range = list(iter_dates(args.start_date, args.end_date))
    profiles = build_sku_profiles(args)

    ensure_output_directory(args.output)

    with args.output.open("w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["date", "sku", "demand_units", "on_hand", "lead_time_days", "product_name"])
        for row in generate_rows(profiles, date_range, args):
            writer.writerow(row)

    total_rows = len(date_range) * len(profiles)
    print(f"Wrote {total_rows} rows to {args.output}")


if __name__ == "__main__":
    main()
