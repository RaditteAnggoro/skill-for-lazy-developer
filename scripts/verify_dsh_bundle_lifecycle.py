"""Install, fail-open, and uninstall the DSH memory bundle in a disposable profile."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BUNDLE = ROOT / "integrations/dsh/companion-memory"
PACKAGE_NAME = "@local/dsh-companion-memory"


class VerifyError(RuntimeError):
    pass


def _run(command, cwd, env, timeout=180):
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return completed


def _profile_path(dsh_home, profile):
    return Path(dsh_home) / "profiles" / profile


def _copy_profile(source, target):
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    package = target / "package.json"
    data = json.loads(package.read_text(encoding="utf-8"))
    data["name"] = "dsh-profile-" + target.name
    package.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


def verify(dsh, dsh_home, source_profile, profile, bundle, artifacts):
    dsh = Path(dsh)
    dsh_home = Path(dsh_home).resolve()
    bundle = Path(bundle).resolve()
    source = _profile_path(dsh_home, source_profile)
    target = _profile_path(dsh_home, profile)
    if not source.is_dir():
        raise VerifyError("source profile not found: {}".format(source))
    if not dsh.is_file():
        raise VerifyError("dsh binary not found: {}".format(dsh))
    env = {**os.environ, "DSH_HOME": str(dsh_home)}
    _copy_profile(source, target)
    result = {
        "schema_version": 1,
        "run_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "profile": str(target),
        "checks": {},
    }

    install = _run(
        [str(dsh), "plugin", "--profile", profile, "add", str(bundle)],
        ROOT,
        env,
    )
    if install.returncode != 0:
        raise VerifyError("bundle install failed: {}".format((install.stderr or install.stdout)[-1200:]))
    result["install"] = install.stdout.strip().splitlines()[-3:]

    config = _run([str(dsh), "--profile", profile, "--dump-config"], ROOT, env)
    if config.returncode != 0:
        raise VerifyError("profile config failed: {}".format((config.stderr or config.stdout)[-1200:]))
    result["checks"]["bundle_rows"] = "engram-mcp" in config.stdout and "engram-guard" in config.stdout

    run = _run([str(dsh), "--profile", profile, "Reply with exactly: OK"], ROOT, env)
    result["fail_open"] = {
        "returncode": run.returncode,
        "stdout": run.stdout.strip()[-500:],
        "stderr": run.stderr.strip()[-1000:],
    }
    result["checks"]["fail_open"] = run.returncode == 0 and "OK" in run.stdout

    remove = _run(
        [str(dsh), "plugin", "--profile", profile, "remove", PACKAGE_NAME],
        ROOT,
        env,
    )
    if remove.returncode != 0:
        raise VerifyError("bundle uninstall failed: {}".format((remove.stderr or remove.stdout)[-1200:]))
    result["uninstall"] = remove.stdout.strip().splitlines()[-3:]

    after = _run([str(dsh), "--profile", profile, "--dump-config"], ROOT, env)
    result["checks"]["rows_removed"] = (
        after.returncode == 0
        and "engram-mcp" not in after.stdout
        and "engram-guard" not in after.stdout
    )
    run_after = _run([str(dsh), "--profile", profile, "Reply with exactly: OK"], ROOT, env)
    result["checks"]["still_works"] = (
        run_after.returncode == 0 and "OK" in run_after.stdout
    )
    result["ok"] = all(result["checks"].values())
    Path(artifacts).mkdir(parents=True, exist_ok=True)
    (Path(artifacts) / "dsh-bundle-lifecycle.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dsh", type=Path, default=Path("/Applications/DeepSeek Harness.app/Contents/Resources/runtime/cli/bin/dsh"))
    parser.add_argument("--dsh-home", type=Path, required=True)
    parser.add_argument("--source-profile", default="dsh-eval")
    parser.add_argument("--profile", default="dsh-lifecycle")
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--artifacts", type=Path, default=ROOT / ".agents/artifacts/dsh-bundle")
    args = parser.parse_args(argv)
    try:
        result = verify(
            args.dsh,
            args.dsh_home,
            args.source_profile,
            args.profile,
            args.bundle,
            args.artifacts,
        )
    except (OSError, VerifyError, subprocess.TimeoutExpired) as exc:
        print("DSH bundle lifecycle failed: {}".format(exc), file=sys.stderr)
        return 1
    print(json.dumps(result["checks"], indent=2))
    print("DSH bundle lifecycle: {}".format("PASS" if result["ok"] else "FAIL"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
