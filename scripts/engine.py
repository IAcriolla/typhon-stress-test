
import os
import json
import time
import datetime
import argparse
import subprocess
import urllib.request
import urllib.error

# PATH CONFIGURATION
SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TyphonEngine:
    def __init__(self, url, model, context_size, iterations, growth, extra_params=None):
        self.url = url
        self.model = model
        self.context_size = context_size
        self.iterations = iterations
        self.growth = growth
        self.extra_params = extra_params or {}
        self.hardware_info = self._detect_hardware()
        self.results = []

    def _detect_hardware(self):
        info = {"gpu_name": "Unknown", "vram_total_mb": 0, "cuda_version": "Unknown"}
        try:
            output = subprocess.check_output(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"], encoding='utf-8').strip().split('\n')
            if output:
                parts = output[0].split(',')
                info["gpu_name"] = parts[0].strip()
                info["vram_total_mb"] = int(parts[1].strip())
            
            cuda_output = subprocess.check_output(["nvcc", "--version"], encoding='utf-8', stderr=subprocess.STDOUT)
            for line in cuda_output.split('\n'):
                if "release" in line:
                    info["cuda_version"] = line.strip()
                    break
        except Exception as e:
            print(f"⚠️ [TYPHON] Hardware detection failed: {e}")
        return info

    def _get_current_vram(self):
        try:
            output = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], encoding='utf-8')
            return int(output.strip().split('\n')[0])
        except: return 0

    def run_test(self):
        print(f"🔥 [TYPHON] Iniciando Stress Test...")
        print(f"💻 Hardware: {self.hardware_info['gpu_name']} ({self.hardware_info['vram_total_mb']} MB VRAM)")
        print(f"{'Etapa':<8} | {'Contexto':<12} | {'VRAM Usada (MB)':<15} | {'TPS':<8} | {'Latencia (s)':<10}")
        print("-" * 70)

        dummy_text = "token " * 1000
        history = []
        current_ctx = 1024

        for i in range(self.iterations):
            # Build history to simulate context growth
            history.append({"role": "user", "content": dummy_text * (current_ctx // 1024)})
            
            payload = {
                "model": self.model,
                "messages": history,
                "temperature": 0.1,
                "max_tokens": 100
            }

            try:
                req = urllib.request.Request(self.url, data=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
                start_time = time.time()
                with urllib.request.urlopen(req, timeout=120) as response:
                    resp_data = json.loads(response.read().decode('utf-8'))
                    end_time = time.time()

                duration = end_time - start_time
                content = resp_data['choices'][0]['message']['content']
                tokens_gen = max(1, len(content) // 4)
                tps = tokens_gen / duration
                vram_used = self._get_current_vram()

                print(f"{i+1:<8} | {current_ctx:<12,} | {vram_used:<15} | {tps:<8.2f} | {duration:<10.2f}")

                self.results.append({
                    "step": i + 1,
                    "context_size": current_ctx,
                    "vram_used_mb": vram_used,
                    "tps": tps,
                    "latency_sec": duration
                })

                # Prepare next iteration
                current_ctx += self.growth
                history.append({"role": "assistant", "content": content})

            except Exception as e:
                print(f"❌ Error en etapa {i+1}: {e}")
                break

        self._save_log()

    def _save_log(self):
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_model = self.model.replace('/', '_').replace(':', '_')
        filepath = os.path.join(SKILL_ROOT, "logs", f"test_{safe_model}_{timestamp}.json")
        
        log_data = {
            "metadata": {
                "timestamp": datetime.datetime.now().isoformat(),
                "model": self.model,
                "hardware": self.hardware_info,
                "config": {"iterations": self.iterations, "growth": self.growth, "context_limit": self.context_size}
            },
            "results": self.results
        }
        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=4)
        print(f"\n✅ Log guardado: {filepath}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--ctx", type=int, default=131072)
    parser.add_argument("--iter", type=int, default=5)
    parser.add_argument("--growth", type=int, default=8192)
    args = parser.parse_args()

    engine = TyphonEngine(args.url, args.model, args.ctx, args.iter, args.growth)
    engine.run_test()
