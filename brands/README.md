# Brand packs

One folder per brand, holding `brand.json`. `example/` is a made-up brand (Fieldnote) for tests.

| Field | What it holds | Used by |
| --- | --- | --- |
| `id`, `name` | Folder name and display name | everything |
| `mission` | One sentence | `brand_strategy`, voice prompt |
| `strategy` | List of `{title, body}` | `brand_strategy` |
| `voice.principles` | How the brand writes | `brand_strategy` (read by the model) |
| `voice.avoid` | Exact words and phrases not to use | `lint_copy`, video negative prompt |
| `palette` | `{name, hex, group, text_on_it}`; hex lower case, six digits | palette, colour checks |
| `typefaces` | `{name, role, styles}` | typography, CSS font check |
| `art_direction` | `{id, title, intro, role, covers, swatches}` | imagery briefs, video plan |
| `tokens.color` | CSS variable -> hex | CSS colour check |
| `tokens.font` | CSS variable -> list of families, brand face first | CSS font check |
| `tokens.spacing` | CSS variable -> px | CSS spacing check |
| `tokens.duration` | CSS variable -> ms | CSS duration check |
| `tokens.font_size`, `line_height`, `easing` | Reference values | `brand_typography`, `brand_tokens` |

Optional: `source` (where the values came from; put the repository and commit here) and
`fictional`.

A pack that is missing something is refused when it is loaded, with a list of what is wrong.
