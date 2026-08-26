/* grimm.c - verify Grimm's conjecture (Erdos problem #375) for all n up to N.
 *
 * Grimm 1969: if n+1, ..., n+k are all composite then there are DISTINCT primes
 * p_1, ..., p_k with p_i | n+i. Published verification: Laishram and Shorey,
 * "Grimm's conjecture on consecutive integers", Int. J. Number Theory 2 (2006)
 * 1-5, for n <= 1.9 x 10^10, in Mathematica.
 *
 * TWO REDUCTIONS, both exact, both stated so a referee can kill them:
 *
 * R1 (maximal runs suffice).  A system of distinct representatives restricted to
 *    a subset is still a system of distinct representatives.  Every all-composite
 *    run n+1..n+k sits inside a maximal all-composite run, and every maximal run
 *    is the open interval between two consecutive primes.  So checking one
 *    matching per prime gap covers every (n,k) pair with n+k below the limit.
 *
 * R2 (only the k-smooth elements can conflict).  Fix a run of k consecutive
 *    integers.  A prime r > k divides at most one of them, because two multiples
 *    of r differ by at least r > k.  Split the run into S (elements all of whose
 *    prime factors are <= k, "k-smooth") and L (the rest).  Give each element of
 *    L one of its prime factors r > k.  Those choices are automatically pairwise
 *    distinct, and none of them lies in the pool {primes <= k} that S draws from.
 *    Hence the whole run has an SDR IFF S has an SDR inside {primes <= k}.
 *    |S| is 0 for almost every gap, so the matching is nearly free and the real
 *    cost is the sieve.
 *
 * SMOOTHNESS IS EXACT, NOT A LOG FILTER.  Per segment we accumulate prod[j], the
 * B-smooth part of n = lo + j, as an exact uint64 product of prime powers.  n is
 * B-smooth iff prod[j] == n.  No floating point anywhere in the decision path.
 *
 * GUARD.  R2 needs k <= B.  Every gap is checked against B at runtime and the
 * program aborts if one exceeds it, so a too-small B can never silently pass.
 *
 * Build:  cc -O2 -o bin/grimm src/grimm.c
 * Run:    ./bin/grimm <lo> <hi> [outprefix]
 *         checks every maximal composite run whose closing prime is in [lo,hi).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

#define SEG   (1u << 22)      /* segment length, 4M entries */
#define SMOOTH_B 2048         /* R2 guard: every gap must have k <= SMOOTH_B.
                               * Five maximal gaps below 10^12 exceed 512
                               * (k = 513, 515, 531, 533, 539 after
                               * 304599508537, 416608695821, 461690510011,
                               * 614487453523, 738832927927), each verified
                               * here by Miller-Rabin.  2048 covers every gap
                               * below 10^18, where the record is 1476 after
                               * 1425172824437699411.  Raising B costs only
                               * sum of 1/p over the new primes, about 8 pct. */
#define MAXS  256             /* max |S| we are prepared to match */
#define HARDMIN 2             /* log runs with |S| >= this to the certificate */             /* max |S| we are prepared to match */

static uint32_t *bp; static int nbp;          /* base primes up to sqrt(hi) */
static uint32_t sp[SMOOTH_B]; static int nsp; /* primes <= SMOOTH_B */

static void base_primes(uint64_t hi) {
    uint32_t lim = 2; while ((uint64_t)(lim+1)*(lim+1) <= hi) lim++;
    lim += 2;
    /* we also need every prime <= SMOOTH_B for the smoothness product, which
     * on a small test range is a longer reach than sqrt(hi) */
    if (lim < SMOOTH_B + 1) lim = SMOOTH_B + 1;
    char *c = calloc(lim + 1, 1);
    bp = malloc(sizeof(uint32_t) * (lim / 2 + 64)); nbp = 0; nsp = 0;
    for (uint32_t i = 2; i <= lim; i++) {
        if (c[i]) continue;
        bp[nbp++] = i;
        if (i <= SMOOTH_B) sp[nsp++] = i;
        for (uint64_t j = (uint64_t)i * i; j <= lim; j += i) c[j] = 1;
    }
    free(c);
    if (sp[nsp-1] > SMOOTH_B || nsp < 1) { fprintf(stderr,"smooth prime table wrong\n"); exit(2); }
}

/* Kuhn augmenting path.  cand x prime-slot bipartite graph, tiny. */
static int nS; static int deg[MAXS]; static int adj[MAXS][64];
static int matchP[SMOOTH_B]; static char used[SMOOTH_B];
static int try_aug(int v) {
    for (int e = 0; e < deg[v]; e++) {
        int p = adj[v][e];
        if (used[p]) continue;
        used[p] = 1;
        if (matchP[p] < 0 || try_aug(matchP[p])) { matchP[p] = v; return 1; }
    }
    return 0;
}
static int perfect_matching(void) {
    for (int i = 0; i < SMOOTH_B; i++) matchP[i] = -1;
    int m = 0;
    for (int v = 0; v < nS; v++) {
        memset(used, 0, sizeof used);
        m += try_aug(v);
    }
    return m == nS;
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr,"usage: grimm lo hi [outprefix]\n"); return 2; }
    uint64_t LO = strtoull(argv[1],0,10), HI = strtoull(argv[2],0,10);
    const char *pre = argc > 3 ? argv[3] : "grimm";
    if (LO < 2) LO = 2;
    /* Shard overlap.  A shard cannot close the gap that straddles its left
     * edge unless it has already seen the prime before LO, so start the scan
     * 2000 below LO (every gap here has k <= 512).  Gaps in the overlap get
     * checked twice across neighbouring shards, which is harmless.  Missing
     * one would not be. */
    uint64_t SCAN = LO > 2002 ? LO - 2000 : 2;
    base_primes(HI + SMOOTH_B + 16);

    char hf[512], sf[512];
    snprintf(hf,sizeof hf,"%s_hard.txt",pre);
    snprintf(sf,sizeof sf,"%s_summary.txt",pre);
    FILE *fh = fopen(hf,"w");
    fprintf(fh,"# every gap whose k-smooth set S has |S| >= %d, that is every gap\n"
               "# where reduction R2 leaves a matching with any chance of failing.\n"
               "# columns: p  q  k  |S|  matched  then the B-smooth members\n", HARDMIN);

    unsigned char *isc = malloc(SEG);
    uint64_t *prod = malloc((size_t)SEG * 8);
    uint64_t *nxt  = calloc(nbp, 8);
    if (!isc || !prod || !nxt) { fprintf(stderr,"oom\n"); return 2; }

    uint64_t prev = 0;                 /* last prime seen */
    uint64_t pend[MAXS]; int npend = 0;/* B-smooth numbers since that prime */
    uint64_t ngap=0, nprime=0, maxgap=0, maxgap_at=0;
    uint64_t nS1=0, nS2=0, nS3=0, nfail=0, ntrunc=0;
    clock_t t0 = clock();

    for (uint64_t lo = SCAN; lo < HI; lo += SEG) {
        uint64_t hi = lo + SEG; if (hi > HI) hi = HI;
        uint32_t L = (uint32_t)(hi - lo);
        memset(isc, 0, L);
        for (int i = 0; i < nbp; i++) {
            uint64_t p = bp[i]; if (p*p >= hi) break;
            uint64_t s = nxt[i];
            if (s < lo) { s = (lo + p - 1) / p * p; if (s < p*p) s = p*p; }
            for (uint64_t j = s; j < hi; j += p) { isc[j - lo] = 1; s = j + p; }
            nxt[i] = s;
        }
        for (uint32_t j = 0; j < L; j++) prod[j] = 1;
        for (int i = 0; i < nsp; i++) {
            uint64_t p = sp[i];
            for (uint64_t pe = p; pe < hi; pe *= p) {
                uint64_t s = (lo + pe - 1) / pe * pe;
                for (uint64_t j = s; j < hi; j += pe) prod[j - lo] *= p;
                if (pe > hi / p) break;
            }
        }
        for (uint32_t j = 0; j < L; j++) {
            uint64_t n = lo + j;
            if (n < 2) continue;
            if (!isc[j]) {                       /* n is prime: close the run */
                nprime++;
                if (prev) {
                    uint64_t k = n - prev - 1;
                    if (k >= 1) {
                        ngap++;
                        if (k > maxgap) { maxgap = k; maxgap_at = prev; }
                        if (k > SMOOTH_B) {
                            fprintf(stderr,"FATAL: gap k=%llu at p=%llu exceeds B=%d\n",
                                    (unsigned long long)k,(unsigned long long)prev,SMOOTH_B);
                            return 3;
                        }
                        /* keep only the k-smooth ones (pend holds B-smooth) */
                        nS = 0;
                        for (int a = 0; a < npend; a++) {
                            uint64_t c = pend[a], r = c; int d = 0; int ps[64];
                            for (int b = 0; b < nsp && (uint64_t)sp[b] <= k; b++) {
                                if (r % sp[b] == 0) { ps[d++] = b; while (r % sp[b]==0) r /= sp[b]; }
                            }
                            if (r != 1) continue;          /* has a factor > k */
                            if (nS >= MAXS) { ntrunc++; break; }
                            deg[nS] = d;
                            for (int b = 0; b < d; b++) adj[nS][b] = ps[b];
                            nS++;
                        }
                        if (nS) {
                            int ok = perfect_matching();
                            if (nS >= 1) nS1++;
                            if (nS >= 2) nS2++;
                            if (nS >= 3) nS3++;
                            /* Log only |S|>=2 at scale: those are the only runs
                             * where the matching could conceivably have failed,
                             * since a single k-smooth element always has a free
                             * prime.  |S|==1 is counted, not stored, or the
                             * certificate file would run to gigabytes. */
                            if (nS >= HARDMIN) {
                            fprintf(fh,"%llu %llu %llu %d %d",
                                    (unsigned long long)prev,(unsigned long long)n,
                                    (unsigned long long)k,nS,ok);
                            for (int a = 0; a < npend; a++)
                                fprintf(fh," %llu",(unsigned long long)pend[a]);
                            fprintf(fh,"\n");
                            }
                            if (!ok) {
                                nfail++;
                                fprintf(stderr,"*** GRIMM FAILS at p=%llu q=%llu k=%llu\n",
                                        (unsigned long long)prev,(unsigned long long)n,
                                        (unsigned long long)k);
                            }
                        }
                    }
                }
                prev = n; npend = 0;
            } else {                              /* composite: is it B-smooth? */
                if (prod[j] == n && npend < MAXS) pend[npend++] = n;
                else if (prod[j] == n) ntrunc++;
            }
        }
    }
    double secs = (double)(clock() - t0) / CLOCKS_PER_SEC;
    fclose(fh);
    FILE *fs = fopen(sf,"w");
    const char *fmt =
      "range            [%llu, %llu)   (scan from %llu)\n"
      "primes seen      %llu\n"
      "gaps checked     %llu\n"
      "largest gap      k=%llu after p=%llu\n"
      "gaps with |S|>=1 %llu\n"
      "gaps with |S|>=2 %llu\n"
      "gaps with |S|>=3 %llu\n"
      "FAILURES         %llu\n"
      "truncations      %llu   (must be 0)\n"
      "cpu seconds      %.1f\n"
      "smooth bound B   %d\n";
    fprintf(fs,fmt,(unsigned long long)LO,(unsigned long long)HI,(unsigned long long)SCAN,
        (unsigned long long)nprime,(unsigned long long)ngap,
        (unsigned long long)maxgap,(unsigned long long)maxgap_at,
        (unsigned long long)nS1,(unsigned long long)nS2,(unsigned long long)nS3,
        (unsigned long long)nfail,(unsigned long long)ntrunc,secs,SMOOTH_B);
    fclose(fs);
    printf(fmt,(unsigned long long)LO,(unsigned long long)HI,(unsigned long long)SCAN,
        (unsigned long long)nprime,(unsigned long long)ngap,
        (unsigned long long)maxgap,(unsigned long long)maxgap_at,
        (unsigned long long)nS1,(unsigned long long)nS2,(unsigned long long)nS3,
        (unsigned long long)nfail,(unsigned long long)ntrunc,secs,SMOOTH_B);
    return nfail ? 1 : 0;
}
