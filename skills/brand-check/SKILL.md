---
name: brand-check
description: Use when writing or changing CSS, UI copy, or image and video briefs for the brand served by the `brand` MCP server. Covers reading the brand before making anything and checking the result before showing it.
version: 0.1.0
---

# Making work that follows the brand

The brand lives in the `brand` MCP server. Do not recall its colours, typefaces, spacing or wording
from memory: read them, every time.

## Before making anything

1. Call `brand_strategy`. It returns the mission, the strategy points and the voice principles.
2. Call the tool for the part you are about to make:
   - colour: `brand_palette`
   - type: `brand_typography`
   - spacing, motion: `brand_tokens` with the category
   - imagery or video: `brand_art_direction`

## After making it

| You made | Call | Then |
| --- | --- | --- |
| CSS | `lint_css` with the whole stylesheet | Fix every error. Fix warnings unless there is a reason not to, and say the reason. |
| Copy | `lint_copy` with the text | Reword every flagged phrase. Then reread the copy against the voice principles yourself: the tool checks listed words only, not tone. |
| A text and background colour pair | `check_contrast` | Body text needs 4.5, large text 3.0. If it fails, pick another brand colour; do not adjust the colour. |
| A colour that is not from the palette | `nearest_brand_colour` | Use the brand colour it returns. |

Run the check again after fixing. Show the work only when the check reports no errors.

## When the brand does not cover it

If a tool returns nothing for what you need (no lens for that kind of image, no token for that
size), say so and ask. Do not invent a value and present it as the brand's.
