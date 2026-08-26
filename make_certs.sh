#!/bin/sh
# Assemble the small, git-kept certificate bundle from the big gitignored run
# output in data/.  Everything here must be small enough to read by hand and
# complete enough that somebody else can re-derive the claim.
set -e
cd "$(dirname "$0")"
mkdir -p certs

{
  echo "# Grimm's conjecture (Erdos problem 375) run certificate"
  echo "# assembled $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
  echo "# host: $(uname -srm)   cc: $(cc --version 2>&1 | head -1)"
  echo "# source sha256: $(shasum -a 256 src/grimm.c | cut -d' ' -f1)  src/grimm.c"
  echo "# verifier sha256: $(shasum -a 256 verify_375.py | cut -d' ' -f1)  verify_375.py"
  echo
  echo "## sieve validation, must read primes seen 455052511"
  cat data/pi1e10_summary.txt 2>/dev/null || echo "(not run)"
  echo
  echo "## shard summaries"
  for f in data/shard_*_summary.txt; do
    [ -e "$f" ] || continue
    echo "--- $f"
    cat "$f"
  done
} > certs/grimm_run.txt

# the genuinely tight cases: every gap whose k-smooth set has 4 or more members
{
  echo "# every prime gap found with |S| >= 4, that is every run where the"
  echo "# matching in reduction R2 had four or more elements competing for the"
  echo "# primes below the gap length.  columns: p q k |S| matched then the"
  echo "# B-smooth members of the run.  recheck any row with:"
  echo "#   python3 verify_375.py interval <p> <k>"
  grep -hv '^#' data/shard_*_hard.txt data/pi1e10_hard.txt 2>/dev/null \
    | awk '$4 >= 4' | sort -n -k1,1 -u
} > certs/grimm_hardest.txt

echo "certs/grimm_run.txt      $(wc -l < certs/grimm_run.txt) lines"
echo "certs/grimm_hardest.txt  $(wc -l < certs/grimm_hardest.txt) lines"
