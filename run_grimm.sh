#!/bin/sh
# Push Grimm's conjecture (Erdos #375) past the published 1.9 x 10^10 bar.
#
# 12 equal shards of [2, 10^12), 3 running at once.  Each shard starts its scan
# 2000 below its nominal low end so no gap can fall between two shards.  Shards
# are handed to xargs in order, so a partial run still gives a contiguous
# verified prefix: read data/shard_*_summary.txt and take the highest HI whose
# shard and all shards below it finished.
#
#   sh run_grimm.sh [HI] [LANES]
set -e
HI=${1:-1000000000000}
LANES=${2:-3}
N=12
mkdir -p data
: > data/shards.list
i=0
while [ $i -lt $N ]; do
  lo=$(( HI / N * i ));  [ $i -eq 0 ] && lo=2
  hi=$(( HI / N * (i+1) )); [ $((i+1)) -eq $N ] && hi=$HI
  printf '%02d %s %s\n' "$i" "$lo" "$hi" >> data/shards.list
  i=$((i+1))
done
cat data/shards.list | xargs -P "$LANES" -L1 sh -c \
  './bin/grimm $1 $2 data/shard_$0 > data/shard_$0.log 2>&1; echo "shard $0 done $(date +%H:%M:%S)"'
echo "ALL SHARDS DONE"
grep -h FAILURES data/shard_*_summary.txt | sort | uniq -c
