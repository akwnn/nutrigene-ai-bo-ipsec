# Cross-check 1 — three open blockers vs. Hall, Lin & Ogle 2025 (Sci Rep 15:24479)

Source PDF: `/Users/jy/BO/s41598-025-09256-9.pdf` (15 pp).

**Method note (so the readings below can be audited or rejected).** `pdftoppm`/poppler is not
installed, so the Read tool could not rasterise pages. Instead: (a) text and both design tables were
extracted with `pypdf` in `extraction_mode="layout"`, which renders Tables 1 and 2 as
column-aligned ASCII — these are *printed table* readings, not figure readings; (b) the Figure 1/2/3
raster images were pulled from the PDF at native embedded resolution (Fig 1 1654×2258, Fig 2
1800×1596, Fig 3 1472×2453) and measured directly. Fig 2a axis calibration: y=0 at pixel row 737.5,
ticks every 80.667 px, 0–9 (1 px = 0.0124 response units). The calibration is corroborated by the
measured box medians reproducing the digitizer's own dot-medians to ±0.02 on 6 of the columns where
both are unambiguous (cols 13, 18, 20, 21, 23, 25). Where my line-labelling is uncertain I say so.

---

### Item: Stage-2 argmax — which condition is visually highest in Figure 2a
Source: p. 5, Figure 2a (embedded raster, 1800×1596). Column→row keying confirmed by decoding the
printed circle matrix beneath the panel: 99/100 cells match printed Table 2 (p. 4), so
left-to-right = Table 2 top-to-bottom is established, not assumed.
Finding: Measured box medians, top of the ranking (coded factor levels C/CIV/LN411/FN):

| col | code | **median** | Q1 | Q3 | whisker max | digitizer mean | digitizer dot-median |
|---|---|---|---|---|---|---|---|
| **13** | `0 0 0 -` | **4.00** | 1.47 | 4.67 | 5.82 | 3.67 | 4.06 |
| 18 | `- - + -` | 3.48 | 1.64 | 4.24 | 4.42 | 3.04 | 3.48 |
| 19 | `+ + + -` | 3.48 | 0.94 | 5.39 | 7.49 | 3.38 | 3.29 |
| 9 | `0 - 0 0` | 3.34 | 1.91 | 4.44 | 5.10 | 2.83 | 3.16 |
| 17 | `0 + 0 0` | 2.89 | 1.57 | 5.19 | 6.42 | 3.29 | 3.13 |
| 22 | `0 0 + 0` | 2.79 | — | — | 4.78 | 3.06 | 3.10 |
| 8 | `+ - + -` | 2.25 | 0.92 | 6.83 | 8.60 | 3.09 | 2.25 |

**The argmax depends entirely on which statistic is used**, and the figure does not privilege one:
- highest **median**: col 13 (4.00)
- highest **mean** (digitizer's): col 13 (3.67)
- highest **Q3 / box top**: col 8 (6.83)
- highest **single replicate**: col 8 (8.60)

Note the y-axis of Fig 2a runs to 9, not 4; boxes reach 8.6.
Status: **resolved for the median/mean statistic — stage2_13 is highest. Unresolved as a
statistic-independent fact.** Nothing printed in the paper adjudicates between statistics.
Action: Record that stage2_13 is the argmax under median and under mean, and that col 8 (`+ - + -`,
= stage2_08) is the argmax under Q3 and under max-replicate. Do not state an unqualified "the
published argmax" without naming the statistic.

---

### Item: Are the top stage-2 conditions separable by eye?
Source: p. 5, Figure 2a, columns 8, 9, 13, 17, 18, 19, 22.
Finding: **No — they overlap heavily.** The top five IQRs share a common band of roughly
[1.91, 4.24], about 2.3 response units wide, while the top five medians span only
4.00 − 2.89 = 1.11 units. Concretely: col 13's median (4.00) lies inside the box of col 18
(1.64–4.24), col 19 (0.94–5.39), col 9 (1.91–4.44) and col 17 (1.57–5.19); and cols 18 and 19's
medians (3.48) both lie inside col 13's box (1.47–4.67). Col 8 is the extreme case — the lowest
median of the seven (2.25) but the highest Q3 (6.83) and highest replicate (8.60).

This matches the paper's own account of the assay: p. 4, "*the reason for the discrepancy is likely
due to … high variability in levels of differentiation*"; and Methods p. 12 reports only
"*at least 4 wells from at least 3 experimental replicates*" with no variance reported anywhere.
Status: resolved — the top conditions are **not** visually separable.
Action: **This confirms rank-based replay is the right scope.** Update
`bo-endothelial/data/published/VALIDATION_REPORT.md` §6: B1's "the argmax must be settled" framing
can be closed as *unresolvable from the published figure* rather than *pending*. The recommendation
already in §6 ("scoping the Phase 2 claim to rank recovery … is better supported") is the correct
one and is now supported by direct measurement, not inference.

---

### Item: Does the paper name a best-performing stage-2 condition in text?
Source: p. 4 Results ("Validation of TheO" and the paragraph preceding it), p. 5 Fig. 2 caption,
p. 10 Discussion. Grepped the full extracted text for best/highest/greatest/optimum/optimal/maximum.
Finding: **No.** No row of Table 2 / column of Figure 2a is ever named as best-performing. The only
optimum discussed for stage 2 is the *model-predicted* point: p. 4, "*This prediction solution of
35.6 µg/mL C, 67.2 µg/mL CIV, 0.9 µg/mL LN411, and 22 µg/mL FN is the Theoretical Optimized
formulation (TheO)*". The Fig. 2 caption (p. 5) is purely descriptive of the panels. The Discussion
(p. 10) names only EO, which comes from Figure 3, not from the stage-2 runs.
Status: resolved — the paper is silent. No published text can be contradicted here, and none can
be relied on.
Action: Note in VALIDATION_REPORT.md B1 that the argmax is a quantity the paper never asserts, so
"recovers the published discrete argmax" was never a claim the paper makes about stage 2.
Supplementary Information (Figures S1–S3 are referenced) was not on disk and was not checked.

---

### Item: TheO's coded position, and whether a tested condition sits near it
Source: p. 4 (TheO concentrations); p. 2 Results and p. 12 Methods (factor levels); Table 2 (p. 4).
Finding: TheO = 35.6 C, 67.2 CIV, 0.9 LN411, 22 FN. Stage-2 coded ranges — C 0/35.5/71,
LN411 0/0.8/1.6, FN 22/48.5/75. Coded position:
- C 35.6/71 = **0.501** → the centre
- LN411 0.9/1.6 = **0.563** → just above centre
- FN (22−22)/53 = **0.000** → low
- CIV = **0.600** if the stage-2 high is 112, or **1.200** (outside the design cube) if it is 56

So TheO ≈ `0 0 0 -` on three of four factors under either reading.
**Table 2 row 13 is exactly `0 0 0 -`** — i.e. stage2_13, the condition with the highest measured
median. Coded Euclidean distances under the CIV-high=112 reading: stage2_13 **0.118**, next nearest
stage2_04 (`0 0 0 0`) 0.514, stage2_17 0.643, stage2_18 (`- - + -`) 0.896. Under the CIV-high=56
reading TheO falls outside the cube and the nearest points become stage2_17 (0.542) then
stage2_13 (0.703).

**Counter-evidence that must travel with this, and it is the paper's own text:** p. 4,
"*Interestingly, the TheO formulation resulted in very little endothelial differentiation, around
the level seen on FN alone (Fig. 3a, b)*". Figure 3b confirms it — TheO's box median there is ≈1.0,
one of the lowest of the nine. So proximity to TheO is **not** evidence of high measured CD31
according to the paper's own follow-up experiment, and the paper's data are internally inconsistent
on this point between Fig 2a col 13 and Fig 3b.
Status: unresolved — the geometry favours stage2_13 but the CIV level it depends on is the
unresolved B3 question, and the paper's own validation experiment cuts the other way.
Action: Do not use TheO-proximity as an independent tiebreaker for the argmax. It is entangled with
B3 (Collagen IV high = 56 vs 112) and is contradicted by Fig 3b. Record as context only.

---

### Item: Where the value 4.22 for stage2_18 comes from
Source: p. 5, Figure 2a, column 18.
Finding: Column 18's measured features are box top (Q3) **4.24**, median **3.48**, Q1 1.64, lower
whisker 0.82, upper whisker cap ≈4.38. The digitizer's dot-median for the same column is 3.478 —
an exact match to my measured median line. **4.22 sits on the box top, not the median.** The most
likely explanation for our record's 4.22 is that the box-top line was read as the median for that
column. (Stated as a diagnosis from measurement, not as a printed fact — the paper prints no
numbers for Fig 2a.)
Status: contradicts our record — our extraction's stage2_18 = 4.22 does not correspond to that
column's median.
Action: **Manual check needed before changing anything.** p. 5, Figure 2a, column 18 (18th box from
the left; coded column `- - + -`, i.e. CIV and C light, LN411 dark, FN light). Look at whether the
horizontal line at ≈4.24 is the rectangle's top edge or the median rule, and whether there is a
separate rule at ≈3.48 inside the box. My zoomed read says the rectangle top is at 4.24 with a
distinct median rule at 3.48, but this is a figure reading of a source the authors themselves call
low-resolution and I am not proposing a corrected value.

---

### Item: stage1_23, Laminin 511 — printed coded value
Source: **p. 2, Table 1, row 23** (last row). Independently, p. 3, Figure 1a heatmap, column 23.
Finding: Printed Table 1 row 23 reads verbatim `+   +   +   +   +   -` for C / CIV / LN111 / LN411 /
LN511 / FN. **LN511 = `+` (HIGH).**
The Figure 1a heatmap agrees: I measured all 138 circles in Fig 1a; column 23's LN511 circle has
mean grey **0.0** (pure black = 1 = high), and figure and table agree on **138/138** cells.
Our record's patch reading (grey 0.9, pure black, HIGH) is correct. The third-party digitizer's
`stage1_23` factor_code `+ + + + - -` is wrong in that one cell; it agrees with the printed table on
the other 137.
Status: **resolved — contradicts the digitizer, confirms our record.** Printed value is `+`.
Action: This follows unambiguously from printed Table 1 *and* is independently confirmed by the
printed figure, so it is safe to adopt `+`. **Still flagging it**: it is a change to a delivered data
file and should be recorded as an adopted correction with this citation (p. 2 Table 1 row 23), not
applied silently. Update VALIDATION_REPORT.md B2 to mark this row resolved in favour of the printed
matrix.

---

### Item: stage2_21, Fibronectin — printed coded value
Source: **p. 4, Table 2, row 21**. Also p. 5, Figure 2a heatmap, column 21.
Finding: Printed Table 2 row 21 reads verbatim `-   +   +   +` for C / CIV / LN411 / FN.
**FN = `+` (HIGH).** This **agrees with the digitizer** and **contradicts our patch reading.**

I reproduced our patch reading and it is not a misread: Fig 2a column 21's FN circle measures mean
grey **211.9**, the canonical light/0 value (the palette in Fig 2a is strictly discrete — 0–33 dark,
125–155 mid, 212 light; 212 recurs 37 times with no intermediates). So **the paper is internally
inconsistent at this one cell**: printed Table 2 says `+`, the Fig 2a heatmap says `-`. Every other
cell agrees (99/100).

Decisive structural evidence for the table: taking Table 2 as printed, the 16 non-centre,
non-axial rows form a complete and distinct 2⁴ factorial (all 16 sign combinations present exactly
once) — a valid face-centred CCD. Taking the figure's reading instead, row 21 becomes `- + + -`,
which duplicates row 16 and leaves `- + + +` untested — 15 distinct points, not a valid CCD.
I verified this computationally against both readings.
Status: **contradicts our record.** Printed Table 2 value is `+`; our patch reading of the *figure*
is accurate but the figure disagrees with the table, and the table is the structurally coherent one.
Action: Adopt `+` for stage2_21 FN, citing p. 4 Table 2 row 21. **Still flagging it**: this reverses
a finding currently recorded in VALIDATION_REPORT.md B2 ("Both cells favour the printed matrix over
the CSV" — true for stage1_23, false for stage2_21), so B2 must be rewritten rather than annotated.
Also record the newly-found fact that **Figure 2a's heatmap and Table 2 disagree with each other**
in the published paper — that is a defect in the source, not in either digitization, and it is worth
mentioning if the authors are contacted.

---

### Item: the missing `stage3_fig3b_named_conditions_extracted.csv`
Source: p. 6, **Figure 3b** and its caption; p. 4–5 Results, "Validation of TheO".
Finding: **The paper does have exactly this figure.** Fig 3b is captioned "*Graphical representation
of CD31 area per DAPI area normalized to the FN control for conditions indicated by the heatmap
below the graph*", and the panel contains **9 named formulations**, keyed by a four-row colour matrix
(C / CIV / LN411 / FN) with the legend: black = Maximum, red = Optimized level, grey = 0,
cyan = Starting concentration. Reading them left to right: TheO (all red); TheO-C; TheO-FN (= EO);
EO-C; `++++`; C-dropped `++++`; `+++-`; LN411+FN (LN411 = cyan); FN alone.

This matches the digitizer's description in `EXTRACTION_NOTES.md` line-for-line, including the odd
detail: "*One factor (LN411 concentration in the "LN411+FN" condition) is marked
`unknown_prior_published_conc` — it references a value from a different, earlier paper (ref. 28)*"
— that is precisely the cyan "Starting concentration" circle, and ref. 28 is Hall et al. 2022,
*Stem Cell Rep.* 17:569–583.

Note Fig 3b uses a **different y-scale** from the other panels: it runs to 15, with the EO box
reaching ≈12.7. Fig 1a runs to 4 and Fig 2a to 9.
Status: **unresolved — this item does NOT close.** The reference is not an error. The file describes
real, extractable content that was simply not delivered.
Action: Keep B5 open in VALIDATION_REPORT.md and re-request the file from the digitizer, or extract
Figure 3b independently (p. 6, panel b, 9 columns). Correct B5's wording from "*Either it was omitted
from the handoff or the notes describe work not completed*" — the first branch is now the live one,
since the described content demonstrably exists in the paper.

---

### Item: (incidental) the "figures are low resolution" caption note
Source: p. 3, Figure 1 caption.
Finding: Verbatim in the published caption: "*The lowest level of CD31 expression is indicated by
the bright green and the highest by the dark blue.The resolution of all figures is low, but figure
#1 is especially low.  We have attached the high resolution figure 1 here.*"
Status: resolved — confirms VALIDATION_REPORT.md §4 and contradicts `EXTRACTION_NOTES.md`
lines 48–51, which called the note "spurious… reads like inserted text".
Action: No change needed to VALIDATION_REPORT.md, which already has this right. It does mean a
high-resolution Figure 1 exists and can be requested from ogle@umn.edu — though note it is
**Figure 1**, i.e. stage 1, that the authors supplied at high resolution. Nothing in the paper
suggests a high-resolution **Figure 2** exists, and Figure 2a is where the unresolved argmax lives.
