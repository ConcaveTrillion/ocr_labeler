# MVVM Refactor: Migration Strategy and Metrics

Status: migration planning and measurement guide.

## Migration Strategy

### Incremental rollout

1. Migrate lower-level operations/services first
2. Refactor viewmodels
3. Refactor views to consume updated viewmodels
4. Cleanup remaining state coupling

### Risk management

- Keep changes small and test-backed
- Preserve compatibility where possible during migration
- Use progressive replacement over big-bang rewrites

## Success Metrics

### Code quality

- Lower complexity in views and viewmodels
- Reduced cross-layer import coupling
- Stable/improved maintainability indicators

### Architecture quality

- Clear layer boundaries
- Predictable dependency direction
- Improved layer-level testability

### Delivery quality

- No major regression increase
- Fast local feedback (tests/lint/build)
- Easier feature iteration in UI + operations
