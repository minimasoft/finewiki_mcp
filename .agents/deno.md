# Deno Skills Guide for Linux Environments (LLM Agent Reference)

## Installation

```bash
# Install via curl
curl -fsSL https://deno.land/install.sh | sh

# Verify installation
deno --version

# Update Deno
deno upgrade
```

## Core Commands

| Command | Description |
|---------|-------------|
| `deno run [file]` | Execute JavaScript/TypeScript programs |
| `deno serve [file]` | Start HTTP server (Deno.serve API) |
| `deno fmt [files]` | Format code with Prettier-like formatting |
| `deno lint [files]` | Lint JavaScript/TypeScript code |
| `deno test [files]` | Run tests |
| `deno check [files]` | Check TypeScript types |
| `deno bundle [input] [output]` | Bundle modules into a single file |
| `deno doc [module]` | Show documentation for a module |

## Security Model

Deno implements a granular permission system. Scripts cannot access sensitive resources without explicit permission:

- `--allow-read` - File system read access
- `--allow-write` - File system write access  
- `--allow-net` - Network access (ports, URLs)
- `--allow-env` - Environment variable access
- `--allow-run` - Spawn subprocesses
- `--allow-all` - All permissions

## Common Use Cases

### Web Server Development

```ts
// server.ts
Deno.serve((_req: Request) => {
  return new Response("Hello, world!");
});
```

Run with `deno run --allow-net server.ts`

### File Operations

```ts
// Read file
const text = await Deno.readTextFile("data.txt");

// Write file
await Deno.writeTextFile("output.txt", "Hello");
```

Requires `--allow-read` and `--allow-write` respectively.

### HTTP Client

```ts
const response = await fetch("https://api.example.com/data");
const data = await response.json();
```

Requires `--allow-net`.

### Running Tests

```ts
// test.ts
Deno.test("example test", () => {
  const actual = 1 + 1;
  if (actual !== 2) throw new Error("Test failed!");
});
```

Run with `deno test`

### Using Standard Library

```ts
import { capitalize } from "jsr:@std/text@0.224";
console.log(capitalize("hello")); // "Hello"
```

Or via npm specifiers:
```ts
import express from "npm:express@4.18";
```

## LLM Agent Specific Commands

### Running Scripts with Minimal Permissions

For agent scripts that only need network access (API calls):

```bash
deno run --allow-net agent.ts
```

### Bundling Agents for Deployment

```bash
# Bundle agent into single file
deno bundle agent.ts bundled_agent.js
```

## Environment Variables

Access environment variables with `Deno.env.get()` and `Deno.env.set()`. Requires `--allow-env`.

```ts
const apiKey = Deno.env.get("API_KEY");
```

## Jupyter Integration (for AI/ML Work)

Deno supports running in Jupyter notebooks with TypeScript support:

1. Install the kernel: `deno jupyter --install`
2. Use Deno kernels in Jupyter environments for interactive ML/AI development

## Quick Reference

```bash
# Run script with network access only
deno run --allow-net script.ts

# Format all files in project
deno fmt

# Lint specific file
deno lint src/agent.ts

# Check types without running
deno check src/agent.ts

# Test with coverage
deno test --coverage

# Update dependencies
deno cache --reload deps.ts
```
