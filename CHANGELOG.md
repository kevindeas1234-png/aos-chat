# Changelog

All notable changes to AOS chat. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- `README.md` — the repository previously shipped only `STATUS.md`.
- `CREDITS.md`, `CONTRIBUTING.md`, `SECURITY.md`, `.gitattributes`.

### Changed
- Personal data removed from the documentation.

### Fixed
- **The composer was unusable on a phone.** The text box was `#0b1220` on a `#0b1220` body
  with a `#1d3145` border, so there was nothing visible to tap; `font:15px/1.3 inherit` is
  invalid CSS and was silently discarded; and with no `<form>`, the keyboard's Go key had
  nothing to submit. Now: a visible composer, a real form, `interactive-widget=resizes-content`
  so the keyboard resizes rather than covers, a `100vh` fallback before `100dvh`, and
  `Cache-Control: no-store` so a phone never tests a stale page.
- Token handling: a key is verified against LM Studio's stored SHA-512 hash before it is
  written, so a typo can no longer become a 401 much later.
- Two copies could bind the same port on Windows because `http.server` sets
  `allow_reuse_address`. Now exclusive, and a second launch opens the page instead of
  failing.

## [0.1.0] — 2026-11-15

First tagged release.

- One page, served on the LAN, answering questions about this machine using facts read
  from it rather than guessed by the model.
- Verified facts shown inline with every answer; no facts block when none are needed.
- Self-test written to `selftest.txt` on every start.