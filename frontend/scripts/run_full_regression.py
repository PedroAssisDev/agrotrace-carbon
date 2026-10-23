"""Runner da regressão final (22 passos) sob AGROTRACE_DATA_ROOT temporário.

Por padrão grava o relatório fora do versionamento (temp). Para publicar a
evidência acadêmica sob docs/audits/current/, passe ``--out`` explicitamente.

Uso:
    python scripts/run_full_regression.py
    python scripts/run_full_regression.py --out docs/audits/current/regressao.json
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

FRONTEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = FRONTEND_ROOT.parent
PY = sys.executable

# Unbuffered progress on Windows
try:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except Exception:
    pass


def _run(
    name: str,
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    timeout: int = 900,
) -> dict[str, Any]:
    started = time.perf_counter()
    print(f"\n>>> [{name}] {' '.join(cmd)}")
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        elapsed = int((time.perf_counter() - started) * 1000)
        out = (proc.stdout or "")[-4000:]
        err = (proc.stderr or "")[-2000:]
        summary = out.strip().splitlines()[-3:] if out.strip() else []
        result = {
            "name": name,
            "command": cmd,
            "cwd": str(cwd),
            "exit_code": proc.returncode,
            "duration_ms": elapsed,
            "summary": " | ".join(summary)[:500],
            "stderr_tail": err[-500:] if proc.returncode else "",
        }
        status = "PASS" if proc.returncode == 0 else "FAIL"
        print(f"<<< [{name}] {status} exit={proc.returncode} {elapsed}ms")
        if proc.returncode != 0 and err:
            print(err[-800:])
        return result
    except subprocess.TimeoutExpired:
        elapsed = int((time.perf_counter() - started) * 1000)
        print(f"<<< [{name}] TIMEOUT {elapsed}ms")
        return {
            "name": name,
            "command": cmd,
            "cwd": str(cwd),
            "exit_code": 124,
            "duration_ms": elapsed,
            "summary": "TIMEOUT",
            "stderr_tail": "",
        }
    except Exception as exc:
        elapsed = int((time.perf_counter() - started) * 1000)
        return {
            "name": name,
            "command": cmd,
            "cwd": str(cwd),
            "exit_code": 1,
            "duration_ms": elapsed,
            "summary": f"{type(exc).__name__}: {exc}",
            "stderr_tail": "",
        }


def _inventory(label: str, data_root: Path) -> dict[str, Any]:
    cycles = list((data_root / "cycles").glob("*.json")) if (data_root / "cycles").exists() else []
    return {
        "label": label,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "data_root_name": data_root.name,
        "cycle_count": len(cycles),
        "db_files": [p.name for p in (data_root / "db").glob("*")] if (data_root / "db").exists() else [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help=(
            "Caminho do relatório JSON. Default: arquivo temporário "
            "(não sobrescreve docs/audits/current/regressao.json)."
        ),
    )
    parser.add_argument("--skip-forge", action="store_true")
    parser.add_argument("--quick", action="store_true", help="Skip long e2e (smoke/full cycle)")
    args = parser.parse_args()

    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        data_root = Path(tmp) / "agrotrace-data"
        data_root.mkdir(parents=True, exist_ok=True)
        env = os.environ.copy()
        env["AGROTRACE_DATA_ROOT"] = str(data_root)
        env["PYTHONUTF8"] = "1"
        # Ensure blockchain package importable
        bc = str(REPO_ROOT / "agrotrace-carbon-blockchain-service")
        env["PYTHONPATH"] = os.pathsep.join(
            filter(None, [bc, str(FRONTEND_ROOT), env.get("PYTHONPATH", "")])
        )

        inv_before = _inventory("before", data_root)
        results.append({"name": "inventory_initial", "exit_code": 0, "duration_ms": 0, "summary": json.dumps(inv_before)})

        # 2-8 service tests
        suites = [
            ("save-file", REPO_ROOT / "agrotrace-carbon-save-file", [PY, "-m", "unittest", "discover", "-s", "tests", "-q"]),
            ("wrappers", REPO_ROOT / "agrotrace-carbon-wrappers-service", [PY, "-m", "pytest", "-q", "--tb=line"]),
            ("ontology", REPO_ROOT / "agrotrace-carbon-ontology-manager", [PY, "-m", "pytest", "-q", "--tb=line"]),
            ("calculation", REPO_ROOT / "agrotrace-carbon-calculation-service", [PY, "-m", "pytest", "-q", "--tb=line"]),
            ("model-training", REPO_ROOT / "agrotrace-carbon-model-training-service", [PY, "-m", "pytest", "-q", "--tb=line"]),
            ("traceability", REPO_ROOT / "agrotrace-carbon-traceability-service", [PY, "-m", "pytest", "-q", "--tb=line"]),
            (
                "blockchain",
                REPO_ROOT / "agrotrace-carbon-blockchain-service",
                [PY, "-m", "pytest", "tests/", "-m", "not blockchain_local and not sepolia", "-q", "--tb=line"],
            ),
        ]
        for name, cwd, cmd in suites:
            if cwd.exists():
                results.append(_run(name, cmd, cwd=cwd, env=env, timeout=600))
            else:
                results.append({"name": name, "exit_code": 1, "duration_ms": 0, "summary": "dir missing", "command": cmd})

        # 9 forge
        contracts = REPO_ROOT / "agrotrace-carbon-blockchain-service" / "contracts"
        if not args.skip_forge and contracts.exists():
            results.append(_run("forge_build", ["forge", "build"], cwd=contracts, env=env, timeout=300))
            results.append(_run("forge_test", ["forge", "test", "-vvv"], cwd=contracts, env=env, timeout=300))
        else:
            results.append({"name": "forge_build", "exit_code": 0, "duration_ms": 0, "summary": "skipped", "command": []})
            results.append({"name": "forge_test", "exit_code": 0, "duration_ms": 0, "summary": "skipped", "command": []})

        # 10 frontend tests
        results.append(
            _run("frontend_tests", [PY, "-m", "pytest", "tests/", "-q", "--tb=line"], cwd=FRONTEND_ROOT, env=env, timeout=600)
        )

        # 11 all validate_* (unique by resolved path — evita duplicatas no Windows)
        validate_scripts = sorted(
            {p.resolve(): p for p in (FRONTEND_ROOT / "scripts").glob("validate_*.py")}.values(),
            key=lambda p: p.name.lower(),
        )
        for script in validate_scripts:
            results.append(
                _run(
                    script.stem,
                    [PY, str(script), "--data-root", str(data_root)],
                    cwd=FRONTEND_ROOT,
                    env=env,
                    timeout=600,
                )
            )

        if not args.quick:
            # 12-13 smoke + full emission
            for stem in ("run_pipeline_smoke_test", "test_full_emission_cycle"):
                script = FRONTEND_ROOT / "scripts" / f"{stem}.py"
                if script.exists():
                    results.append(
                        _run(stem, [PY, str(script), "--data-root", str(data_root)], cwd=FRONTEND_ROOT, env=env, timeout=900)
                    )

            # 14-21 specialised scenarios already covered by validate_* where available;
            # extras:
            extras = [
                "validate_correction_recalculation",
                "validate_reproducibility",
                "validate_maintainability_extensibility",
                "validate_prediction_separation",
                "validate_technical_audit",
                "validate_temporal_model",
            ]
            # already run in validate_* loop — mark provenance/raw recovery via technical audit

        # scan secrets
        results.append(
            _run("scan_secrets", [PY, str(FRONTEND_ROOT / "scripts" / "scan_secrets.py")], cwd=FRONTEND_ROOT, env=env, timeout=300)
        )

        inv_after = _inventory("after", data_root)
        results.append({"name": "inventory_final", "exit_code": 0, "duration_ms": 0, "summary": json.dumps(inv_after)})

        # Git identity (may be empty / slow on large untracked trees)
        git_info: dict[str, Any] = {}
        try:
            gh = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(REPO_ROOT),
                capture_output=True,
                text=True,
                timeout=30,
            )
            git_info["commit"] = gh.stdout.strip() if gh.returncode == 0 else None
            # Avoid full `git status` on huge untracked trees (can take minutes)
            git_info["status"] = "skipped_full_status_for_performance"
            git_info["note"] = "branch may have no commits yet"
        except Exception as exc:
            git_info["error"] = type(exc).__name__

        report = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "python": sys.version,
            "data_root": str(data_root),
            "inventory_before": inv_before,
            "inventory_after": inv_after,
            "git": git_info,
            "results": results,
            "pass_count": sum(1 for r in results if r.get("exit_code") == 0),
            "fail_count": sum(1 for r in results if r.get("exit_code") not in (0, None)),
        }

        out_path = args.out
        if out_path is None:
            out_path = Path(tempfile.gettempdir()) / f"agrotrace-regressao-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        else:
            out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n=== REGRESSION SUMMARY === pass={report['pass_count']} fail={report['fail_count']}")
        print(f"report: {out_path}")
        if args.out is None:
            print("(default temp path — use --out docs/audits/current/regressao.json to publish)")
        for r in results:
            if r.get("exit_code") != 0:
                print(f"  FAIL {r.get('name')}: exit={r.get('exit_code')} {r.get('summary', '')[:120]}")

        return 0 if report["fail_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
