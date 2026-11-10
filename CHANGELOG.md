# Changelog

All notable changes to the blueprint. Versions follow [Semantic Versioning](https://semver.org/).

## 1.1.0 – unreleased

### Changed

- **The wait survives restarts.** Instead of a state trigger with `for:` (which Home Assistant resets on every restart), the automation looks every 15 minutes for updates whose wait is over. A restart during the wait no longer skips the check; the wait starts again for updates that are still pending.
- Automatic runs only happen when something is due, so idle ticks leave no traces and do not update "last triggered".

### Added

- Optional input **Remember checked versions**: a text helper in which the automation notes the checked versions. With it, restarts never cause a second check of the same version, and a newer version that replaces a pending one is checked as well.
- Version number in the blueprint description and this changelog.
- Runtime tests that run the blueprint in a real Home Assistant test instance (wait, restart, memory, manual run, failure text).

## 1.0.0 – 2026-10-25

First version: Grok checks a pending update after a configurable wait and sends a verdict (Install / Wait / Caution) with up to three reported problems to the phone and, optionally, the full answer with sources as a Home Assistant notification. Manual runs check all pending updates.
