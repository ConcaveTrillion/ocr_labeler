# Solo OCR Labeling Strategy (Limited Daily Time)

This plan is optimized for one person working on 1900-era book OCR with limited time each day.

## Goals

1. Maximize OCR quality gain per hour.
1. Keep labeling sustainable day-to-day.
1. Build a validation set that gives reliable training decisions.

## Core Priorities

1. Label quality and representativeness matter more than raw page count.
1. Increase validation set first (so training signals are trustworthy).
1. Focus effort on hard pages where OCR fails most.
1. Iterate: label -> train -> inspect failures -> relabel targeted cases.

## Recommended Dataset Targets

1. Validation pages:

   - Minimum: 30-50 pages
   - Better: 75-150 pages

1. Training pages:

   - Minimum: 150-300 pages
   - Better quality run: 400-800 pages

1. Split:

   - Use roughly 80/20 (or 85/15 if total data is small)
   - Keep both sets representative of fonts, scan quality, layout type, and degradation

## What To Label First (Highest ROI)

1. Body text paragraphs (high-frequency content)
1. Degraded pages: faint print, bleed-through, skew, gutter shadow
1. Typography edge cases: italics, small caps, footnotes, drop caps
1. Layout edge cases: marginalia, multi-column transitions, running headers

## Labeling Quality Rules (Fast and Practical)

Before marking a page done:

1. No obvious missed lines
1. No incorrectly merged lines
1. Boxes are reasonably tight and readable

Daily QA:

1. Recheck 10-20% of pages labeled that day

Weekly QA:

1. Recheck pages where model output looked worst

## Daily Time-Boxed Checklists

## 30-Minute Day

1. 20 min: label high-impact pages only (hard/noisy pages)
1. 10 min: quick QA of what you just labeled

Target throughput:

- 5-10 pages/day, depending on complexity

## 60-Minute Day

1. 10 min: pick pages (mix easy + hard)
1. 35 min: label
1. 10 min: quick QA pass
1. 5 min: export/update train-val assignment

Target throughput:

- 8-15 pages/day

## 90-Minute Day

1. 10 min: page selection and scope for session
1. 55 min: labeling
1. 15 min: QA pass
1. 10 min: export/update assignment + notes on failure patterns

Target throughput:

- 15-30 pages/day

## Weekly Cadence

1. Monday-Tuesday: throughput focus (new pages)
1. Wednesday: cleanup focus (fix weak labels and hard pages)
1. Thursday: add underrepresented page styles
1. Friday: training + evaluation + next-week failure list

## Training Cadence

1. Keep validation fixed once it reaches target size.
1. Add most new pages to training.
1. Retrain weekly (or every 2-3 days if you have enough additions).
1. Select best checkpoint using validation plus real OCR output quality.

## Failure-Driven Loop (Most Efficient Improvement Method)

1. Run model on unlabeled or weakly labeled pages.
1. Identify repeat failure patterns (missed faint lines, merged lines, etc.).
1. Label/correct pages that contain those exact patterns.
1. Retrain.
1. Repeat.

## Suggested Tracking Sheet (Simple)

Track these columns each day:

1. Date
1. Minutes spent
1. Pages labeled
1. Pages QA-reviewed
1. New pages added to train
1. New pages added to val
1. Top 3 failure patterns noticed

## Stop/Continue Heuristic During Training

1. Continue if validation clearly improves and OCR text quality improves on holdout pages.
1. Stop when validation mostly oscillates and text quality changes are negligible.
1. Improve data/config, not just epochs, once plateauing starts.

## Practical Recommendation for Your Current Situation

1. Increase validation first to at least 40 pages.
1. Grow training to at least 250-300 pages.
1. Keep focusing on hard historical pages rather than easy clean pages.
1. Retrain and compare OCR output on a fixed holdout set weekly.
