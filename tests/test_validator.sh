#!/usr/bin/env bash
# Proves the guardrails actually bite. A validator that never fails is theatre.
set -u
cd "$(dirname "$0")/.."
fail=0

echo "== the real store must be clean =="
python3 scripts/validate.py || fail=1

echo
echo "== the invalid fixtures must be rejected =="
out=$(python3 scripts/validate.py --root tests/fixtures/invalid 2>&1)
code=$?
echo "$out"
if [ $code -eq 0 ]; then
  echo "FAIL: invalid fixtures passed validation"; fail=1
fi

for expected in \
  "sourced only from 'agent:'" \
  "nested mapping is not allowed" \
  "must match filename stem" \
  "is in the future" \
  "does not match required grammar" \
  "does not exist" \
  "broken relative link"
do
  if ! grep -qF "$expected" <<<"$out"; then
    echo "FAIL: expected violation not detected: $expected"; fail=1
  fi
done

echo
[ $fail -eq 0 ] && echo "ALL TESTS PASSED" || echo "TESTS FAILED"
exit $fail
