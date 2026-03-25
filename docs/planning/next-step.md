# Next Step: Event-Scoped UI Updates

Goal: replace broad page-level refresh behavior with targeted, typed
state-change events so views update only the necessary UI elements.

## Scope for the First Vertical Slice

- Focus first on word style toggles (`I`, `SC`, `BL`) end-to-end.
- Keep existing full-refresh path as fallback for safety.
- Remove ad-hoc refresh suppression gates once event flow is stable.

## Checklist

1. **Define event model (state layer)**
   - Add a typed event payload for word-style updates.
   - Include at minimum: `page_index`, `line_index`, `word_index`, `italic`, `small_caps`, `blackletter`.
   - Keep event names explicit (for example, `word_style_changed`).

2. **Add event emission in mutation operations**
   - Emit `word_style_changed` after successful `update_word_attributes` writes.
   - Ensure emit happens only on successful mutation.
   - Preserve existing broad notifications for backward compatibility during migration.

3. **Add event subscription in coordinator (`TextTabs`)**
   - Register listener for typed word-style events.
   - Route event to `WordMatchView` targeted update API instead of full `update_from_page`.
   - Unregister listener during teardown to avoid stale callbacks.

4. **Add targeted update API in `WordMatchView`**
   - Add method for style-only updates by `(line_index, word_index)`.
   - Update only local style state + style button colors.
   - Avoid rebuilding line/word containers for this event type.

5. **Define precedence rules between events and full refresh**
   - If typed event arrives, apply targeted update immediately.
   - If full page update arrives for the same change window, dedupe/coalesce to prevent duplicate repaint.
   - Keep behavior deterministic under rapid clicks.

6. **Migrate away from suppression gate**
   - Remove one-shot skip flags once typed-event path is proven.
   - Keep temporary compatibility for one release cycle if needed.

7. **Tests: unit + integration coverage**
   - Verify style edit emits `word_style_changed` exactly once.
   - Verify `TextTabs` consumes event and does not call full `update_from_page` for style-only change.
   - Verify `WordMatchView` updates button state without line/word rerender.
   - Verify rapid toggles produce correct final style state.
   - Verify fallback full refresh still works for structural edits.

8. **Instrumentation and observability**
   - Add debug log markers for event emitted, event consumed, targeted update applied.
   - Add a lightweight counter for full refresh vs targeted updates (debug builds/logging only).

9. **Rollout and cleanup**
   - Ship style slice first.
   - Repeat same pattern for:
     - word GT edit events,
     - bbox fine-tune/rebox events,
     - structural word/line changes (which may still require broader rerender scope).
   - Remove obsolete suppression/dedupe workarounds introduced for interim fixes.

## Done Criteria

- Clicking `I`, `SC`, or `BL` updates only the corresponding style controls and local model state.
- No full `_update_lines_display` call is triggered by style-only edits.
- All existing tests pass, and new event-path regressions are green.
- Logs clearly show typed event flow from mutation to targeted UI update.
