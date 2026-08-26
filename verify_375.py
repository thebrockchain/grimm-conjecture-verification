#!/usr/bin/env python3
"""verify_375.py - independent checker for Grimm's conjecture (Erdos #375).

This is the trust anchor and it deliberately shares NO code and NO reduction
with src/grimm.c.  It does the naive thing: full trial-division factorisation of
every element of every maximal composite run, the FULL bipartite graph on all
prime divisors (not just the small ones), and a matching written from scratch.

It is slow on purpose.  Its job is to prove that the fast sweeper's two
reductions (maximal runs suffice, and only the k-smooth elements can conflict)
did not throw away a real counterexample.

Usage:
  python3 verify_375.py range LO HI          # brute force a whole range
  python3 verify_375.py gaps FILE            # recheck the gaps in a *_hard.txt
  python3 verify_375.py crosscheck LO HI FILE [minS]  # calibration gate.  minS must
                                             # match HARDMIN in src/grimm.c (2)
  python3 verify_375.py sample FILE [N]      # recheck N random certificate rows
  python3 verify_375.py interval N K         # one explicit (n, k)

Exit status 0 means every run checked has a system of distinct representatives.
"""
import sys


def primes_upto(n):
    s = bytearray([1]) * (n + 1)
    s[0:2] = b"\0\0"
    i = 2
    while i * i <= n:
        if s[i]:
            s[i * i::i] = bytearray(len(s[i * i::i]))
        i += 1
    return [i for i in range(n + 1) if s[i]]


def factor_primes(n, base):
    """Every distinct prime divisor of n, by trial division. No shortcuts."""
    out, r = [], n
    for p in base:
        if p * p > r:
            break
        if r % p == 0:
            out.append(p)
            while r % p == 0:
                r //= p
    if r > 1:
        out.append(r)
    return out


def is_prime(n, base):
    if n < 2:
        return False
    for p in base:
        if p * p > n:
            return True
        if n % p == 0:
            return n == p
    return True


def matching(sets):
    """Kuhn. sets[i] is the allowed primes for element i. Returns True iff a
    system of distinct representatives exists."""
    assign = {}

    def aug(i, seen):
        for p in sets[i]:
            if p in seen:
                continue
            seen.add(p)
            if p not in assign or aug(assign[p], seen):
                assign[p] = i
                return True
        return False

    for i in range(len(sets)):
        if not aug(i, set()):
            return False
    return True


def check_run(n, k, base):
    """n+1..n+k, assumed all composite. True iff Grimm holds for this run."""
    sets = [factor_primes(n + i, base) for i in range(1, k + 1)]
    return matching(sets), sets


def do_range(lo, hi):
    base = primes_upto(int(hi ** 0.5) + 2)
    print(f"brute force checking every maximal composite run in [{lo},{hi})")
    prev, bad, runs, biggest = None, 0, 0, 0
    for n in range(max(2, lo), hi):
        if is_prime(n, base):
            if prev is not None and n - prev - 1 >= 1:
                k = n - prev - 1
                runs += 1
                biggest = max(biggest, k)
                ok, _ = check_run(prev, k, base)
                if not ok:
                    bad += 1
                    print(f"*** FAIL n={prev} k={k}")
            prev = n
    print(f"runs checked {runs}, largest k {biggest}, failures {bad}")
    return bad


def do_sample(path, count, seed=12345):
    """Recheck a random sample of rows from a certificate file, from scratch.
    A full recheck of a 10^12 run is not affordable in Python, so the sample
    plus every high-|S| row is the honest compromise: state the sample size."""
    import random
    rows = []
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            t = line.split()
            rows.append((int(t[0]), int(t[1]), int(t[2]), int(t[3])))
    if not rows:
        print("no rows")
        return 0
    hi_s = [r for r in rows if r[3] >= 4]          # always take the hardest
    rnd = random.Random(seed)
    pick = hi_s + rnd.sample(rows, min(count, len(rows)))
    pick = sorted(set(pick))
    top = max(q for _, q, _, _ in pick)
    base = primes_upto(int(top ** 0.5) + 2)
    bad = 0
    for pp, q, k, ns in pick:
        if q - pp - 1 != k or not is_prime(pp, base) or not is_prime(q, base):
            print(f"*** BAD ROW {pp} {q} {k}"); bad += 1; continue
        if any(is_prime(pp + i, base) for i in range(1, k + 1)):
            print(f"*** RUN NOT ALL COMPOSITE after {pp}"); bad += 1; continue
        S = smooth_set(pp, k, base)
        if len(S) != ns:
            print(f"*** |S| MISMATCH at {pp}: brute {len(S)} vs file {ns}"); bad += 1
        ok, _ = check_run(pp, k, base)
        if not ok:
            print(f"*** GRIMM FAILS n={pp} k={k}"); bad += 1
    print(f"sampled {len(pick)} of {len(rows)} rows in {path} "
          f"(all {len(hi_s)} rows with |S|>=4, plus {count} random, seed {seed})")
    print(f"failures {bad}")
    return bad


def do_gaps(path):
    """Recheck every gap listed in a grimm *_hard.txt, from scratch."""
    rows = []
    with open(path) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            t = line.split()
            rows.append((int(t[0]), int(t[1]), int(t[2])))
    if not rows:
        print("no rows to check")
        return 0
    top = max(q for _, q, _ in rows)
    base = primes_upto(int(top ** 0.5) + 2)
    bad = 0
    for p, q, k in rows:
        if q - p - 1 != k:
            print(f"*** BAD ROW p={p} q={q} k={k}")
            bad += 1
            continue
        if not is_prime(p, base) or not is_prime(q, base):
            print(f"*** NOT A PRIME GAP p={p} q={q}")
            bad += 1
            continue
        for i in range(1, k + 1):
            if is_prime(p + i, base):
                print(f"*** RUN NOT ALL COMPOSITE at {p+i}")
                bad += 1
        ok, _ = check_run(p, k, base)
        if not ok:
            print(f"*** GRIMM FAILS n={p} k={k}")
            bad += 1
    print(f"rechecked {len(rows)} gaps from {path}, failures {bad}")
    return bad



def smooth_set(n, k, base):
    """The k-smooth elements of the run n+1..n+k, computed from scratch."""
    out = []
    for i in range(1, k + 1):
        f = factor_primes(n + i, base)
        if f and max(f) <= k:
            out.append(n + i)
    return out


def do_crosscheck(lo, hi, hardfile, minS=2):
    """The real calibration gate.  Brute force every maximal composite run in
    [lo,hi), compute the k-smooth subset S from scratch, and demand that the C
    sweeper's hard file lists EXACTLY the runs with S non-empty and EXACTLY the
    same |S| for each.  A silent miss in the sieve or the smoothness product
    shows up here as a diff."""
    base = primes_upto(int(hi ** 0.5) + 2)
    mine = {}
    prev = None
    for n in range(max(2, lo), hi):
        if is_prime(n, base):
            if prev is not None and n - prev - 1 >= 1:
                k = n - prev - 1
                S = smooth_set(prev, k, base)
                if len(S) >= minS:
                    ok, _ = check_run(prev, k, base)
                    mine[(prev, n, k)] = (len(S), ok)
            prev = n
    theirs = {}
    with open(hardfile) as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            t = line.split()
            theirs[(int(t[0]), int(t[1]), int(t[2]))] = (int(t[3]), bool(int(t[4])))
    # the C file's last gap may be cut off by the segment boundary, ignore rows
    # whose closing prime is at or beyond hi
    theirs = {g: v for g, v in theirs.items() if g[1] < hi}
    only_mine = sorted(set(mine) - set(theirs))
    only_theirs = sorted(set(theirs) - set(mine))
    disagree = sorted(g for g in set(mine) & set(theirs) if mine[g] != theirs[g])
    print(f"brute force found {len(mine)} runs with |S| >= {minS}")
    print(f"sweeper file listed {len(theirs)} in the same window")
    print(f"MISSED BY SWEEPER  {len(only_mine)}")
    for g in only_mine[:10]:
        print(f"   {g} brute={mine[g]}")
    print(f"EXTRA IN SWEEPER   {len(only_theirs)}")
    for g in only_theirs[:10]:
        print(f"   {g} sweeper={theirs[g]}")
    print(f"|S| OR VERDICT DISAGREEMENTS {len(disagree)}")
    for g in disagree[:10]:
        print(f"   {g} brute={mine[g]} sweeper={theirs[g]}")
    bad = len(only_mine) + len(only_theirs) + len(disagree)
    print("CALIBRATION PASS" if bad == 0 else "CALIBRATION FAIL")
    return bad


def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 0
    if a[0] == "range":
        return 1 if do_range(int(a[1]), int(a[2])) else 0
    if a[0] == "sample":
        return 1 if do_sample(a[1], int(a[2]) if len(a) > 2 else 200) else 0
    if a[0] == "crosscheck":
        return 1 if do_crosscheck(int(a[1]), int(a[2]), a[3],
                                  int(a[4]) if len(a) > 4 else 2) else 0
    if a[0] == "gaps":
        return 1 if do_gaps(a[1]) else 0
    if a[0] == "interval":
        n, k = int(a[1]), int(a[2])
        base = primes_upto(int((n + k) ** 0.5) + 2)
        ok, sets = check_run(n, k, base)
        for i in range(1, k + 1):
            print(f"  {n+i}: {sets[i-1]}")
        print("SDR exists" if ok else "*** NO SDR")
        return 0 if ok else 1
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
