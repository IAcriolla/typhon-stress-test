#!/bin/bash

# CONFIGURATION
SKILL_DIR="$(dirname "$(readlink -f "$0")")"
TYPHON="$SKILL_DIR/typhon.py"
URL="http://localhost:8080/v1/chat/completions"
MODEL="gemma-4-26B"

echo "🚀 [TYPHON] Starting SOFT RAMP test to find the VRAM wall..."

# We want steps like: 1k, 16k, 32k, 48k
# Starting at 1024, growth 15360, iterations 4
# 1: 1024
# 2: 16384
# 3: 31744
# 4: 47104

python3 "$TYPHON" run --model "$MODEL" --url "$URL" --iter 4 --growth 15360

echo -e "\n✍️ [TYPHON] Synchronizing the Chronicle..."
python3 "$TYPHON" sync

echo -e "\n🧠 [TYPHON] Training the Oracle..."
python3 "$TYPHON" train

echo -e "\n🔮 [TYPHON] Consulting the Oracle for the new limit..."
# Let's ask for 40k, 50k, 60k to see where it predicts the drop
python3 "$TYPHON" recommend --model "$MODEL" --ctx 40000
python3 "$TYPHON" recommend --model "$MODEL" --ctx 50000
python3 "$TYPHON" recommend --model "$MODEL" --ctx 60000

echo -e "\n✅ SOFT RAMP CYCLE COMPLETED"
