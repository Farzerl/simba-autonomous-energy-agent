# Run SIMBA locally

The product demo is fully local after setup and never sends facility state to a
cloud service. All electrical actions stay in the emulator.

## Ubuntu 22.04

```bash
chmod +x setup_ubuntu.sh run_simba_demo.sh download_model.sh
./setup_ubuntu.sh
./run_simba_demo.sh
```

Open `http://127.0.0.1:8000/?tab=agent` if the browser does not open. Select a
language, choose a resilience test, and press **Run resilient demo**.

To validate without a browser:

```bash
.venv/bin/python scripts/smoke_test_agent.py
.venv/bin/python -m pytest -q
```

The GGUF is not required for the deterministic product demo. Download it only for
the separate Gate 1 model-profile path:

```bash
./setup_ubuntu.sh --with-model
.venv/bin/python scripts/adtc_preflight.py --require-model --allow-placeholders
```

## Windows

Double-click `RUN_SIMBA_AGENT.bat`, or run:

```powershell
py -3 scripts/run_demo.py
```

If required packages are missing, run `INSTALL_SIMBA_AGENT.bat` once. The launcher
reports missing Python, missing dependencies and occupied ports in plain language.

## Expected result

- State: `TARGET_MET`
- At least one complication detected and one replan recorded
- Critical-load actions: `0`
- Live electrical control: `disabled`
- A positive verified headroom below the configured peak limit

Use Ctrl+C in the terminal to stop the local server.
