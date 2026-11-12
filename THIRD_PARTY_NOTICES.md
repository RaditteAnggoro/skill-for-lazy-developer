# Third-party software notices

Codex Developer Skills itself is **MIT © 2026 Raditte Anggoro and contributors**.
The distributed skills are plain instruction and metadata files with no required
runtime package.

## Development and fixture dependencies

These packages are not vendored into the release archive. They are installed only when
running the referenced development checks. The versions below match the pinned
development manifests; transitive dependencies are resolved by the package manager and
are not copied into the distributed skill instructions.

| Package | Pinned version | License | Purpose |
| --- | --- | --- | --- |
| [PyYAML](https://github.com/yaml/pyyaml) | 6.0.3 | MIT | Repository and fixture validation |
| [tiktoken](https://github.com/openai/tiktoken) | 0.12.0 | MIT | Optional token measurement |
| [jsonschema](https://github.com/python-jsonschema/jsonschema) | 4.25.1 | MIT | Enhancement evidence schema tests |
| [playwright-core](https://github.com/microsoft/playwright) | 1.56.0 | Apache-2.0 | UI fixture browser checks |
| [pngjs](https://github.com/pngjs/pngjs) | 7.0.0 | MIT | Screenshot decoding |
| [pixelmatch](https://github.com/mapbox/pixelmatch) | 6.0.0 | ISC | Screenshot comparison |
| [React](https://github.com/facebook/react) | 19.1.1 | MIT | React fixture |
| [Vite](https://github.com/vitejs/vite) | 7.1.7 | MIT | React fixture build |
| [Next.js](https://github.com/vercel/next.js) | 15.5.29 | MIT | Next.js fixture |

`tiktoken` may install `requests`, `regex`, `certifi`, `idna`, `urllib3`, and
`charset-normalizer` as transitive development dependencies. `jsonschema` uses
`attrs`, `referencing`, `jsonschema-specifications`, `rpds-py`, and, on some Python
versions, `typing-extensions`. `next` may install
`sharp` as an optional image dependency. Review the installed package metadata and
license texts before redistributing a modified tool bundle.

Python and its standard library retain the
[Python Software Foundation License](https://docs.python.org/3/license.html).
GitHub-hosted CI uses `actions/checkout` and `actions/setup-python`; those actions are
development services and are not included in the release archive.

This inventory is an attribution aid, not a substitute for upstream license text.
Projects credited as inspiration are listed separately in
[docs/SOURCES.md](docs/SOURCES.md); they are not dependencies or bundled source.
