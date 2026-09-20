# Grimm's conjecture, verified to 10^12

If n+1, ..., n+k are all composite, distinct primes p_i divide each n+i.
Erdos problem 375, Guy B32.

## The hunt (landed)

- Target: extend the verified range past Laishram and Shorey 2006 (1.9 * 10^10).
- Result: every maximal all composite run below **10^12** has a system of
  distinct prime representatives. Extends the previous bound by a factor of
  **52.6**. Zero counterexamples. Zero truncations.
- Total CPU: 12,562.7 seconds (3.49 core hours) on an M5, 87 minutes wall.

## Why this repo is PUBLIC

The approved comment on erdosproblems.com problem 375 cites this URL. Making
it private would break a live citation. This is one of only two public repos
in the whole `science/` campaign. Treat every commit accordingly.

## Run it

- Resume with `/napoleon`.
- Reproduce: `sh check.sh` (about two minutes). Adds `full` for the pi(10^10)
  sieve validation.
- The check is written for a skeptic: NOTHING in it trusts `src/grimm.c`.
  Five gates including calibration against pi(10^8) and pi(10^10), sharding
  exactness, and certificate re derivation by `verify_375.py`.

## The guard that makes it believable

B is the smoothness bound. **If a run needs a prime above B, the program
records a truncation instead of silently returning success.** Five maximal
gaps below 10^12 exceed 512, so shards 03 onward ran at B = 2048.
Truncations across the full range: 0.

## Lessons that apply here

- [[science-campaigns]] Five step method, and this repo is the reference
  implementation of "guard the risky assumption".
- [[an-instrument-that-agrees-has-not-been-tested]] `verify_375.py` re derives
  certificates from scratch. Plant a bad one to prove it fails.
- [[measure-dont-claim-the-edge]] 52.6x is exact. State the CPU and the
  hardware.
- [[erdosproblems-account-and-moderation]] The approved comment on problem 375
  is our own; keep it accurate.

## Fleet rules

The fleet rules live in the brock root's CLAUDE.md. PUBLIC, so the no dashes
and no AI look rules bite hardest. Math hunts as a whole stay off the public
portfolio. **Auto-loaded only on a MERGED checkout**
([../CLAUDE.md](../CLAUDE.md), Brockchain-Personal), where the brock root is
this folder's parent; on a SPLIT one it is a sibling
([../brock/CLAUDE.md](../brock/CLAUDE.md), Brockchains-MBP) and nothing
loads it for you, so open it yourself.
