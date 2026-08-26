#!/bin/sh
# check.sh - everything a stranger needs to run to decide whether to believe
# the Grimm's conjecture (Erdos problem 375) claim in RESULTS.md.
#
# Nothing here trusts src/grimm.c.  Steps 1 and 2 build it and prove it agrees
# with a naive brute force that shares no code and no reduction with it.  Step 3
# checks it against two independently known constants.  Step 4 re-derives a
# random sample of the actual run certificate from scratch.
#
#   sh check.sh          quick, about two minutes
#   sh check.sh full     adds the pi(10^10) sieve validation, about two more
set -e
cd "$(dirname "$0")"
mkdir -p bin data
echo "== 0. build"
cc -O2 -o bin/grimm src/grimm.c
echo "== 1. calibration gate: sweeper vs naive brute force on [2, 2x10^6)"
./bin/grimm 2 2000000 data/check_cal > /dev/null
python3 verify_375.py crosscheck 2 2000000 data/check_cal_hard.txt 2
echo "== 2. sharding is exact: 3 shards of a range equal 1 run of it"
./bin/grimm 2 5000000 data/check_one > /dev/null
./bin/grimm 2 1700000 data/check_a > /dev/null
./bin/grimm 1700000 3400000 data/check_b > /dev/null
./bin/grimm 3400000 5000000 data/check_c > /dev/null
grep -hv '^#' data/check_one_hard.txt | cut -d' ' -f1-5 | sort -n -u > data/check_one.cut
grep -hv '^#' data/check_a_hard.txt data/check_b_hard.txt data/check_c_hard.txt \
  | cut -d' ' -f1-5 | sort -n -u > data/check_three.cut
if diff -q data/check_one.cut data/check_three.cut > /dev/null; then
  echo "SHARDING EXACT ($(wc -l < data/check_one.cut | tr -d ' ') rows each)"
else
  echo "SHARDING MISMATCH"; exit 1
fi
echo "== 3. the sieve against known constants"
./bin/grimm 2 100000000 data/check_pi8 | grep "primes seen"
echo "   expected: primes seen      5761455    (pi(10^8))"
if [ "$1" = "full" ]; then
  ./bin/grimm 2 10000000000 data/check_pi10 | grep -E "primes seen|largest gap"
  echo "   expected: primes seen      455052511  (pi(10^10))"
  echo "   expected: largest gap      k=353 after p=4302407359"
fi
echo "== 4. re-derive a sample of the run certificate from scratch"
for f in data/shard_*_hard.txt; do
  [ -e "$f" ] || continue
  echo "-- $f"
  python3 verify_375.py sample "$f" 100
done
echo
echo "== 5. read the claim"
sh finalize.sh
