#!/usr/bin/env bash
# Generates the RULER prompts into ./data with NVIDIA/RULER's own prepare.py and the model's tokenizer.
# Needs a clone of https://github.com/NVIDIA/RULER with its requirements installed (RULER=path, default ./RULER),
# and the tokenizer.json directory of the served checkpoint (TOKENIZER=path).
set -u
HERE=$(cd "$(dirname "$0")" && pwd); RULER=${RULER:-$HERE/RULER}; TOK=${TOKENIZER:?set TOKENIZER to the checkpoint directory with tokenizer.json}
cd "$RULER/scripts/data"
TASKS="niah_single_1 niah_single_2 niah_single_3 niah_multikey_1 niah_multikey_2 niah_multikey_3 niah_multivalue niah_multiquery vt cwe fwe qa_1 qa_2"
for L in 32768 65536 131072; do for T in $TASKS; do
  [ -s "$HERE/data/$L/$T/validation.jsonl" ] && continue
  python prepare.py --save_dir "$HERE/data/$L" --benchmark synthetic --task $T \
    --tokenizer_path "$TOK" --tokenizer_type hf --max_seq_length $L --model_template_type base --num_samples 20 > gen_last.err 2>&1 \
    && [ -s "$HERE/data/$L/$T/validation.jsonl" ] && echo "ok $L $T" || echo "FAIL $L $T (see $RULER/scripts/data/gen_last.err)"
done; done
