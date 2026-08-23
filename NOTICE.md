# Notices and third-party components

Copyright 2026 Farai Rashayi and SIMBA-EMS contributors.

The SIMBA source code in this public package is licensed under Apache-2.0. The
licence does not grant permission to use institutional names, marks or confidential
operational data. No confidential raw meter, account or facility dataset is included.

The downloadable language model is **Qwen3-1.7B**, copyright its respective authors
and licensed Apache-2.0. It is downloaded from the official Qwen Hugging Face
repository and is not committed here:

- https://huggingface.co/Qwen/Qwen3-1.7B
- https://huggingface.co/Qwen/Qwen3-1.7B-GGUF

The Gate 1 model path uses **llama.cpp**, distributed under the MIT licence.
llama.cpp is not bundled in this repository.

Python dependencies remain under their upstream licences. The lightweight local
interface directly uses FastAPI, Pydantic and Uvicorn.

Chronos-2 forecasting weights are not redistributed in the clean public package.
Only routing interface metadata is included to document the existing integration.
The reproducible application demo uses a deterministic synthetic fixture with
generic facility names when the full forecasting artifacts are absent.
