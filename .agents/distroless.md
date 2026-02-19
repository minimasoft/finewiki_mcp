---

## 📦 Distroless Container Reference (v2025)

### ✅ Core Principles

- Minimal runtime: **only your app + runtime deps**
- No shell, package manager, or extra utilities (by default)
- Based on Debian 12/13 (`-debian12`, `-debian13`)
- OCI manifests only → ensure tooling is up-to-date
- Signed with cosign (keyless): verify before use

---

### 🧱 Available Image Families (Debian 12 & 13)

| Image Tag (latest) | Runtime / Purpose | Notes |
|--------------------|-------------------|-------|
| `static-debian{12,13}` | Static binaries only | Smallest image (~2 MiB), no libc, no `/bin/sh` |
| `base-debian{12,13}` | glibc-based minimal | Includes standard libs (e.g., `libc6`, `libssl*`) |
| `base-nossl-debian{12,13}` | Like `base`, but **no SSL libs** | Use for non-TLS apps only |
| `cc-debian{12,13}` | C/C++ runtime | `glibc`, `libgcc`, `libstdc++` |
| `java-base-debian{12,13}` | Java base (JRE-less) | For custom JVM packaging |
| `java{17,21,25}-debian{12,13}` | Prebuilt OpenJDK | Java 25 only in `-debian13` |
| `nodejs{20,22,24}-debian{12,13}` | Node.js runtimes | Latest LTS+current versions |
| `python3-debian{12,13}` | Python 3.x (system) | Python 3.11+ in `-debian13` |

> 🔖 **Architecture tags**: Use suffixes like `:latest-amd64`, or rely on manifest lists.

---

### 🚨 Key Constraints & Workarounds

| Issue | Solution |
|-------|----------|
| No shell by default | Use `ENTRYPOINT ["app"]` (array form only!) |
| Empty entrypoint (`[]`) needs CMD as array | e.g., `CMD ["main.py"]` |
| Debugging difficulty | Use `:debug` or `:debug-nonroot` tags, override with `--entrypoint=sh` |
| Missing `ldd` | Copy it in manually (it's a shell script) |

---

### 🔐 Verification & Security

- ✅ All images signed with **keyless cosign**
```bash
cosign verify $IMAGE \
  --certificate-oidc-issuer https://accounts.google.com \
  --certificate-identity keyless@distroless.iam.gserviceaccount.com
```

---

### 📝 Dockerfile Pattern (Best Practice)

```dockerfile
# Build stage
FROM golang:1.23 AS build
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /app

# Runtime — distroless static image
FROM gcr.io/distroless/static-debian12
COPY --from=build /app /
CMD ["/app"]
```

#### Common variants:

| Stack | Base Image |
|-------|------------|
| Go (static) | `gcr.io/distroless/static-debian12` |
| Python 3 | `gcr.io/distroless/python3-debian12` |
| Node.js | `gcr.io/distroless/nodejs20-debian12` |
| Java | `gcr.io/distroless/java21-debian12` |

> 🔄 For debug builds, change final `FROM` to `...:debug` or `...:debug-nonroot`.

---

### 🔍 Debugging Tips

- Use `:debug` image (has busybox `/bin/sh`)
- Override entrypoint:
```bash
docker run -it --entrypoint=sh your-image
```

> 📌 For non-root variants (`nonroot`, `debug-nonroot`), use tag `debug-nonroot`.

---

### ⚙️ Build Tooling Notes

| Tool | Notes |
|------|-------|
| **Docker** | Requires ≥17.05 for multi-stage builds |
| **Bazel + rules_distroless** | Use [`rules_oci`](https://github.com/bazel-contrib/rules_oci) or [`rules_distroless`](https://github.com/GoogleContainerTools/rules_distroless) |
| **Jib / buildpacks** | Must support OCI manifests; verify version |

---

### 📌 Notes on Debian Versions

- `-debian12`: current default (`bookworm`)
- `-debian13`: uses **UsrMerge** scheme (all `/bin`, `/sbin` → `/usr/bin`)
  - When using `rules_distroless`, set `mergedusr = True` for apt packages.

---

### Full sample distroless python with uv

```dockerfile
FROM ghcr.io/astral-sh/uv:bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Configure the Python directory so it is consistent
ENV UV_PYTHON_INSTALL_DIR=/python

# Only use the managed Python version
ENV UV_PYTHON_PREFERENCE=only-managed

# Install Python before the project for caching (pick your version, 3.12 is a exmaple or check .python-version)
RUN uv python install 3.12

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev --no-editable
COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-editable

# Then, use a final image without uv
FROM gcr.io/distroless/cc

# Copy the Python version
COPY --from=builder --chown=python:python /python /python

WORKDIR /app
# Copy the application from the builder
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

# Run the FastAPI application by default or python or any command that gets installed in the venv
CMD ["fastapi", "run", "--host", "0.0.0.0", "/app/.venv/lib/python3.12/site-packages/uv_docker_example"]
```
