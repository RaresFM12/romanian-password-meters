#!/bin/zsh
# usage: scripts/run_attackers.sh [case_study|full] [attacker ...]
set -e
cd "$(dirname $0)/.."
CONFIG=${1:-case_study}
PY=.venv/bin/python
PCFG_PY=${PCFG_PY:-/opt/homebrew/bin/python3.12}
PCFG_DIR=${PCFG_DIR:-$HOME/tools/pcfg_cracker}
PCFG_RULES=ropw_${CONFIG}
W=$PWD/data/reference/wordlists
OUT=$PWD/data/reference/found
RULES=$PWD/data/reference/rules
SESS=$OUT/sessions
HC_RULES=/opt/homebrew/share/hashcat/rules
ONERULE_URL=https://raw.githubusercontent.com/NotSoSecure/password_cracking_rules/master/OneRuleToRuleThemAll.rule
export LC_ALL=C

cfg() { $PY -c "from ropw.config import load_config; c = load_config('config/$CONFIG.yaml')['reference']; print(int($1))"; }
RUN_BUDGET=$(cfg "c['run_budget']")
SMALL=$(cfg "c['smoke_budget']")
budget_of() { cfg "min(c['run_budget'], c['budgets']['$1'])"; }
echo "run budget $RUN_BUDGET, small run $SMALL"

mkdir -p $OUT $RULES $SESS
if [ ! -f $RULES/OneRuleToRuleThemAll.rule ]; then
  curl -sSfL -o $RULES/OneRuleToRuleThemAll.rule $ONERULE_URL
fi
head -n 100000 $W/all.txt > $W/prince_all.txt
for t in ro_top all_top ro_novar_top; do awk '{ print $0 " " }' $W/$t.txt > $W/${t}_space.txt; done

note() { echo "$1 $2" >> $STATUS; }

# session names carry the attacker and run: parallel jobs get the same $RANDOM
hc() { HCN=$((HCN + 1)); hashcat --stdout --session="ropw_${CUR}_${HCN}_$$" "$@" 2>>$LOG; }
# every john call needs its own session file
jn() { john --stdout --session=$SESS/${CUR}_$1_$$ "${@:3}" 2>>$LOG </dev/null; }

stream() {
  setopt localoptions noerrexit
  local a=$1 B=$2
  local prince_cap=$(( B / 20 ))
  case $a in
    A-EN)
      hc -r $HC_RULES/best66.rule $W/en.txt; note best66 $?
      hc -r $RULES/OneRuleToRuleThemAll.rule $W/en.txt; note onerule $? ;;
    A-RO|A-ALL|A-RO-NOVAR)
      case $a in
        A-RO) list=$W/ro.txt; top=ro_top ;;
        A-ALL) list=$W/all.txt; top=all_top ;;
        A-RO-NOVAR) list=$W/ro_novar.txt; top=ro_novar_top ;;
      esac
      hc -r $HC_RULES/best66.rule $list; note best66 $?
      hc -a 1 $W/$top.txt $W/$top.txt; note combinator $?
      jn prince $a --prince=$W/$top.txt --prince-elem-cnt-min=3 --prince-elem-cnt-max=4 | head -n $prince_cap
      note prince ${pipestatus[1]}
      jn prince_space $a --prince=$W/${top}_space.txt --prince-elem-cnt-min=3 --prince-elem-cnt-max=4 \
        | sed 's/ $//' | head -n $prince_cap
      note prince_space ${pipestatus[1]}
      hc -r $RULES/OneRuleToRuleThemAll.rule $list; note onerule $? ;;
    A-JTR)
      jn rules $a --wordlist=$W/all.txt --rules=Jumbo | head -n $(( B * 6 / 10 )); note jumbo ${pipestatus[1]}
      jn prince $a --prince=$W/prince_all.txt | head -n $(( B * 2 / 10 )); note prince ${pipestatus[1]}
      jn incremental $a --incremental; note incremental $? ;;
    A-PCFG)
      $PCFG_PY $PWD/scripts/pcfg_stdout.py $PCFG_DIR $PCFG_RULES ropw_${CUR}_$$ 2>>$LOG
      note pcfg $? ;;
  esac
}

small_run() {
  STATUS=$OUT/$1.small.status LOG=$OUT/$1.small.log CUR=$1_small
  : > $STATUS; : > $LOG
  # caps from the full budget, so the small run is a prefix of the full run
  stream $1 $(budget_of $1) | head -n $SMALL | awk -v F=$OUT/$1.small.found -v PR=$OUT/$1.probe_candidates \
    -v P=$OUT/$1.positions -v C=$OUT/$1.small.count 'BEGIN { while ((getline l < P) > 0) pos[l] = 1 }
      NR == FNR { t[$0]; next }
      { n++; if ($0 in t) print n ":" $0 > F; if (n in pos) print n ":" $0 > PR }
      END { print n + 0 > C }' \
    data/synthetic/targets_all.txt -
}

full_run() {
  STATUS=$OUT/$1.full.status LOG=$OUT/$1.full.log CUR=$1_full
  : > $STATUS; : > $LOG
  local B=$(budget_of $1)
  stream $1 $B | head -n $B | awk -v C=$OUT/$1.full.count 'NR == FNR { t[$0]; next }
      { n++; if ($0 in t) print n ":" $0 }
      END { print n + 0 > C }' $OUT/targets_with_probes.txt - > $OUT/$1.full.found
}

run_all() {
  local fn=$1; shift
  local pids=()
  for a in "$@"; do $fn $a & pids+=($!); done
  for p in $pids; do wait $p || { echo "a $fn job failed"; exit 1; }; done
}

ALL_ATTACKERS=(A-EN A-RO A-ALL A-JTR A-PCFG A-RO-NOVAR)
if [ $# -gt 1 ]; then ATTACKERS=(${@:2}); else ATTACKERS=($ALL_ATTACKERS); fi

if (( ${ATTACKERS[(Ie)A-PCFG]} )); then
  # one line per account of RockYou without the meter and validation shares (ropw.breach)
  TRAIN=$PWD/data/breach/pcfg_training.txt
  [ -f $TRAIN ] || { echo "$TRAIN missing; run make breach"; exit 1; }
  rm -rf $PCFG_DIR/Rules/$PCFG_RULES
  (cd $PCFG_DIR && $PCFG_PY trainer.py -t $TRAIN -r $PCFG_RULES -e utf-8 \
    </dev/null > $OUT/pcfg_training.log 2>&1)
fi

for a in $ATTACKERS; do
  $PY -m ropw.guess_numbers positions --attacker $a --small $SMALL
  : > $OUT/$a.small.found; : > $OUT/$a.probe_candidates
done
run_all small_run $ATTACKERS
echo "small runs done"
$PY -m ropw.guess_numbers probes --attackers $ALL_ATTACKERS
run_all full_run $ATTACKERS
echo "full runs done"
find $PCFG_DIR -maxdepth 1 -name 'ropw_*.sav' -delete
$PY -m ropw.guess_numbers assemble --attackers $ALL_ATTACKERS --config config/$CONFIG.yaml
{
  echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "run budget: $RUN_BUDGET"
  echo "hashcat: $(hashcat --version)"
  echo "john: $(john 2>/dev/null | head -1)"
  echo "pcfg_cracker: $(cd $PCFG_DIR && git log -1 --format=%h 2>/dev/null)"
  shasum -a 256 $HC_RULES/best66.rule $RULES/OneRuleToRuleThemAll.rule $W/*.txt data/breach/pcfg_training.txt
} | sed "s|$PWD/||" > data/reference/attack_manifest.txt
echo "wrote data/reference/guess_numbers.csv and data/reference/attack_manifest.txt"
