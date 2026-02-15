# NiceGUI Async Refactor Overview

This document summarizes the async/threading direction for NiceGUI integration.

Status: guidance and migration intent; validate details against current implementation.

Last validated: 2026-02-15.

## Problem Statement

Historically, low-level asyncio APIs were used in ways that could interfere with NiceGUI event-loop lifecycle and websocket stability.

## Direction

Use NiceGUI-native async utilities for UI applications:

- `background_tasks.create(...)` for background coroutine scheduling
- `run.io_bound(...)` for blocking I/O
- `run.cpu_bound(...)` for CPU-heavy work when process isolation is needed

## Expected Benefits

- Better websocket stability
- Cleaner async orchestration in UI handlers
- More consistent task lifecycle behavior
- Reduced accidental event-loop misuse
