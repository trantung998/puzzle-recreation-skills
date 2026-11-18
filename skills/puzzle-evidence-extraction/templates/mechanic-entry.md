# Mechanic entry template

Copy one block per mechanic into `evidence/mechanics.md`. Every claim row needs exactly
one label: `Proven`, `Observed`, `Inferred` or `Unknown`. A row with an empty label or an
empty source makes the entry incomplete. Do not mark the `mechanics` phase complete with
an incomplete entry.

Label rules for this file:

- `Proven`: field types and offsets in `dump.cs`, method RVAs, original data bytes, or the
  exact native branch you read (cite file, method index or name, RVA, address space).
- `Observed`: a reference video frame or image (file + timestamp), or an interaction in
  the current Unity project (which run). Static files are never `Observed`.
- `Inferred`: your reconstruction choice, or a rule carried past the branch you read
  (callees or other branches not read). Give the basis. Append it to `decisions.md`.
- `Unknown`: not found, contradictory, or no branch read at all. Say what you searched.
- A class or method name alone proves the code exists. It does not prove a branch, a
  default or when it runs.

---

## <Mechanic name> (`<short-id>`)

- Levels using it (of the N selected): <Stage_003, Stage_007, ...>
- Data that triggers it: <field path and values, for example `board.cells[].kind = 4`>
- Schema: <class, field, type, offset from `dump.cs`> - Proven
- How the code bounds the data: <consuming method and its limit (clamp, skip, max)>,
  or "Unknown: consumer not read". Data beyond that bound is not played.

### Claims

| # | Claim (one testable statement) | Label | Exact source | Case |
|---|---|---|---|---|
| 1 | | | | accept |
| 2 | | | | reject |
| 3 | | | | boundary |

`Case` is accept, reject, boundary, ordering, reset or visual. Model contracts are written
from these rows, so expected results come from the source column, not from new code.

### Branches not read and open questions

- <method or branch, why it matters, label Unknown>

### Inferred choices (each one also appended to `decisions.md`)

- <value or behaviour, basis>

---

## Example (fictional game, for shape only)

## Ice tile (`ice`)

- Levels using it (of the N selected): Stage_006, Stage_009
- Data that triggers it: `cells[].ice = 1..3`
- Schema: `CellData.ice` int at `0x14` (`dump.cs`, class `CellData`) - Proven
- How the code bounds the data: `BoardBuilder.Build` (method 4120, RVA 0x1a2b3c) reads
  `min(ice, 3)`. Values above 3 play as 3.

### Claims

| # | Claim (one testable statement) | Label | Exact source | Case |
|---|---|---|---|---|
| 1 | A tap on an iced cell lowers `ice` by 1 and does not move the piece | Proven | `evidence/native/4188_Cell_OnTap.c`, method 4188, RVA 0x1a40f0, branch `if (this->ice > 0)`; ARM64, Ghidra = image base 0x100000 + RVA | reject |
| 2 | At `ice == 0` the tap moves the piece normally | Proven | same file, `else` branch | accept |
| 3 | Values above 3 are clamped to 3 | Proven | `evidence/native/4120_BoardBuilder_Build.c`, method 4120 | boundary |
| 4 | Crack sound plays on each hit | Inferred | clip `ice_crack` name only; the play call is in method 4190, not read | visual |
| 5 | Shake on a blocked tap | Unknown | searched `Cell` methods and `stringliteral.json` for "shake"; nothing found | visual |

### Branches not read and open questions

- `Cell.OnTapIceBooster` (method 4191): booster bypass of ice. Unknown, not read.

### Inferred choices (each one also appended to `decisions.md`)

- Crack sound on every hit, from the clip name, until method 4190 is read.
