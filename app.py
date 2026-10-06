"""FLOODTAIL — Application entry point.

Phase 1 behaviour:
    1. Load configuration
    2. Initialise logging
    3. Create a RunContext
    4. Display system status
    5. Exit cleanly

No GUI, no Streamlit, no database — backend bootstrap only.
"""

from __future__ import annotations

import sys

from src.config import load_config
from src.logging_config import setup_logging
from src.schemas import RunContext


def main() -> None:
    """Bootstrap the FLOODTAIL backend and display system status."""
    # 1. Load configuration
    cfg = load_config()

    # 2. Initialise logging
    logger = setup_logging(level="INFO")

    logger.info("Configuration loaded from config.yaml")

    # 3. Create a RunContext
    ctx = RunContext(
        model_version=cfg.model.model_version,
        random_seed=cfg.simulation.seed,
        simulation_years=cfg.simulation.years,
        scenario=cfg.project.environment,
    )

    logger.info("RunContext created: %s", ctx.run_id)

    # 4. Display system status
    banner = (
        "\n"
        "============================================\n"
        "  FLOODTAIL\n"
        f"  Version:          {cfg.project.version}\n"
        f"  Environment:      {cfg.project.environment}\n"
        f"  Run ID:           {ctx.run_id}\n"
        f"  Simulation years: {cfg.simulation.years}\n"
        f"  Seed:             {cfg.simulation.seed}\n"
        "  System status:    READY FOR PHASE 2\n"
        "============================================\n"
    )
    logger.info(banner)

    # 5. Exit cleanly
    logger.info("FLOODTAIL backend bootstrap complete.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FLOODTAIL startup failed: {exc}", file=sys.stderr)
        sys.exit(1)
