# Screenshots

Client-side screenshots of `sdmx-data-mcp` in use, referenced from
[`../EXAMPLES.md`](../EXAMPLES.md).

Deliberately kept out of the top-level `README.md`: that file is also the PyPI
landing page, and an image that fails to resolve there renders as a broken tag
on the published project page.

## Expected files

Save screenshots here with these names, then uncomment the matching block in
`EXAMPLES.md`:

| Filename | What it should show |
| --- | --- |
| `01-discovery.png` | `search_dataflows` returning the dataflow list |
| `02-inspect.png` | `inspect_dataflow` with `find_code`, showing available codes |
| `03-get-data.png` | `get_data` returning observations |
| `04-cross-rate.png` | The assistant's synthesis built on retrieved data |
| `05-error.png` | A classified error with its `next_step` |

## Guidance

- Crop to the tool call and its result; full-window captures are unreadable
  once GitHub scales them down.
- Prefer PNG.
- Keep each file under roughly 500 KB. Screenshots are committed to git
  history and cannot be shrunk retroactively without a rewrite.
- Check that no API key, token, internal hostname or private dataset name is
  visible before committing. Anything pushed to a public repository should be
  treated as permanently disclosed.
