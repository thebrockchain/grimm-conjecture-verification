# Grimm's conjecture verified to 10^12

Grimm's conjecture states that if $n+1, \ldots, n+k$ are all composite, then
there exist distinct primes $p_1, \ldots, p_k$ with $p_i \mid n+i$ for each
$i$. It is [Erdos problem 375](https://www.erdosproblems.com/375) and problem
B32 in Guy's collection.

**Result.** Every maximal all-composite run whose closing prime is below
**10^12** has a system of distinct prime representatives. No counterexample
exists below 10^12.

The previous published bound is **1.9 x 10^10** (Laishram and Shorey, 2006),
so this extends the verified range by a factor of **52.6**.

| | |
|---|---|
| Range verified | [2, 10^12), contiguous |
| Prime gaps checked | 37,607,912,844 |
| Counterexamples found | **0** |
| Largest gap encountered | k = 539, after p = 738,832,927,927 |
| Runs needing a nontrivial matching | 166,597 |
| Truncations | 0 |
| Total CPU | 12,562.7 seconds (3.49 core-hours) |

Computed 2026-08-26 on a single Apple M5, twelve shards on three lanes,
87 minutes wall clock.

## Reproduce it

```sh
sh check.sh          # about two minutes
sh check.sh full     # adds the pi(10^10) sieve validation
```

`check.sh` is written for a skeptic. **Nothing in it trusts `src/grimm.c`.**

1. **Calibration gate.** The sweeper is compared against a naive brute force
   that shares no code and no reduction with it, over [2, 2x10^6). Result: 0
   missed, 0 extra, 0 verdict disagreements.
2. **Sharding is exact.** Three shards of a range are diffed row for row
   against a single run of the same range.
3. **The sieve against known constants.** The prime count reproduces
   pi(10^8) = 5,761,455 exactly, and in `full` mode pi(10^10) = 455,052,511
   and the known largest gap k = 353 after p = 4,302,407,359.
4. **Certificate re-derivation.** A sample of the actual run certificate is
   re-derived from scratch by `verify_375.py`, including every row where four
   or more elements competed for the primes below the gap length.

A fifth check comes for free and is the strongest one: summing the twelve
shard prime counts gives 37,607,912,857, which exceeds the known value of
pi(10^12) = 37,607,912,018 by 839, and the eleven deliberate shard overlaps
account for that excess. The sieve therefore reconciles against a published
constant across the entire range.

## Method

For each maximal run of consecutive composite integers between successive
primes p and q, with k = q - p - 1, the task is a bipartite matching between
the k integers and the primes available to divide them. Almost every run is
settled immediately: any member with a prime factor above k is matched to it
uniquely. Only the B-smooth members compete, and the residual matching is
small. 18,400,994 runs needed any reasoning at all, 166,597 needed a
nontrivial matching, and 6,475 had three or more competing elements.

`B` is a smoothness bound used to decide which members can be dismissed
cheaply. **This is the one place the computation can go wrong quietly, so it
is guarded rather than assumed:** if a run needs a prime above `B`, the
program records a truncation instead of silently returning success. Five
maximal gaps below 10^12 exceed 512, so shards 03 onward were run at B = 2048.
Truncations across the full range: 0.

## Certificates

- `certs/grimm_claim.txt` shard by shard summary and the top-level claim
- `certs/grimm_hardest.txt` every run where four or more elements competed,
  with the full member list. Recheck any row with
  `python3 verify_375.py interval <p> <k>`
- `certs/grimm_run.txt` the run log

The full per shard certificates are 315 MB and are not committed. `run_grimm.sh`
regenerates them.

## Also here

`frontier.py` is a triage tool for the Erdos problem database. For a given
problem it pulls `problems.yaml`, the problem page, the **proof claims
thread**, the linked OEIS entries, and a dated arXiv sweep, then writes an
evidence card. It exists because `problems.yaml` has no field for the proof
claims thread, so any triage built on the machine readable data alone is blind
to the source that decides whether a problem is still open.

## What is not claimed

This is a verification, not a proof. Grimm's conjecture remains open. The
computation establishes only that no counterexample exists below 10^12.

## References

- H. P. Grimm, *A conjecture on consecutive composite numbers*, Amer. Math.
  Monthly 76 (1969)
- S. Laishram and T. N. Shorey, *Grimm's conjecture on consecutive integers*,
  Int. J. Number Theory 2 (2006), the 1.9 x 10^10 bound
- K. Ramachandra, T. N. Shorey, R. Tijdeman (1975)
- R. K. Guy, *Unsolved Problems in Number Theory*, problem B32
- T. F. Bloom, Erdos Problem #375, https://www.erdosproblems.com/375
