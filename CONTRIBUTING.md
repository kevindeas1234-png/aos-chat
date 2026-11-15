# Contributing

A small, single-maintainer project. Issues are welcome; pull requests are considered but
not promised. There is no support commitment.

## Before sending anything

Start the app and check the self-test it writes on startup:

```
py chat_server.py --no-browser
```

Then read `selftest.txt`. It should show `/` and `/api/status` returning 200 and
`model probe -> OK`.

## House rules

- **Disclose AI assistance.** If a tool wrote a substantial part of your contribution, say
  so, or use an `Assisted-by:` trailer. `Co-authored-by` is reserved for people.
- **Grounding stays honest.** Machine questions get real facts, and the model is told not
  to invent what the facts do not cover. Do not weaken that to make answers sound better.
- **Never store a credential without verifying it** against the server's stored hash.
- **One change per commit**, with a message that explains why.