
#!/bin/bash

# CONFIGURATION - Using absolute paths to avoid expansion errors
SKILL_DIR="$(dirname "$(readlink -f "$0")")"
TYPHON="$SKILL_DIR/typhon.py"
URL="http://localhost:8080/v1/chat/completions"
MODEL="gemma-4-26B"

echo "🚀 [TYPHON] Starting full automation cycle..."

# 1. Test 4k
echo -e "\n--- Test 1: 4k Context ---"
python3 "$TYPHON" run --model "$MODEL" --ctx 4096 --url "$URL"

# 2. Test 16k
echo -e "\n--- Test 2: 16k Context ---"
python3 "$TYPHON" run --model "$MODEL" --ctx 16384 --url "$URL"

# 3. Test 64k
echo -e "\n--- Test 3: 64k Context ---"
python3 "$TYPHON" run --model "$MODEL" --ctx 65536 --url "$URL"

# 4. Test 128k
echo -e "\n--- Test 4: 128k Context ---"
python3 "$TYPHON" run --model "$MODEL" --ctx 131072 --url "$URL"

echo -e "\n✍️ [TYPHON] Synchronizing the Chronicle..."
python3 "$TYPHON" sync

echo -e "\n🧠 [TYPHON] Training the Oracle..."
python3 "$TYPHON" train

echo -e "\n🔮 [TYPHON] Consulting the Oracle for 90k context..."
python3 "$TYPHON" recommend --model "$MODEL" --ctx 90000

echo -e "\n"
echo "========================================"
echo "✅ FULL CYCLE COMPLETED"
echo "========================================"
