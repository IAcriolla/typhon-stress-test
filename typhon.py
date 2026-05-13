
import subprocess
import sys
import os

# PATH CONFIGURATION
SKILL_ROOT = os.path.dirname(os.path.abspath(__file__))
ENGINE_PATH = os.path.join(SKILL_ROOT, "scripts/engine.py")
SCRIBE_PATH = os.path.join(SKILL_ROOT, "scripts/scribe.py")
DASHBOARD_PATH = os.path.join(SKILL_ROOT, "scripts/dashboard-generator.py")
ORACLE_PATH = os.path.join(SKILL_ROOT, "scripts/oracle.py")

def main():
    if len(sys.argv) < 2:
        print("❌ Error: No command provided.")
        print("Usage: python3 typhon.py [run | sync | view | train | recommend]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "run":
        args = sys.argv[2:]
        print("🔥 [TYPHON] PHASE 1: Executing Stress Test...")
        engine_res = subprocess.run(["python3", ENGINE_PATH] + args)
        
        if engine_res.returncode == 0:
            print("\n✍️ [TYPHON] PHASE 2: Syncing the Chronicle...")
            scribe_res = subprocess.run(["python3", SCRIBE_PATH])
            
            if scribe_res.returncode == 0:
                print("\n📊 [TYPHON] PHASE 3: Generating Dashboard...")
                dash_res = subprocess.run(["python3", DASHBOARD_PATH])
                
                if dash_res.returncode == 0:
                    dashboard_file = os.path.join(SKILL_ROOT, "typhon-dashboard.html")
                    print("\n" + "="*50)
                    print("✅ TYPHON MISSION COMPLETE")
                    print(f"🚀 Dashboard ready: {dashboard_file}")
                    print("="*50)
                else:
                    print("❌ Error generating dashboard.")
            else:
                print("❌ Error syncing chronicle.")
        else:
            print("❌ Error during stress test execution.")

    elif command == "sync":
        subprocess.run(["python3", SCRIBE_PATH])

    elif command == "view":
        subprocess.run(["python3", DASHBOARD_PATH])

    elif command == "train":
        print("🧠 [TYPHON] Training the Oracle (XGBoost)...")
        # We need to add a small wrapper in oracle.py or call it with specific args
        # For now, I'll assume oracle.py has a CLI mode.
        # Let's update oracle.py first to handle CLI.
        subprocess.run(["python3", ORACLE_PATH, "--train"])

    elif command == "recommend":
        # Usage: python3 typhon.py recommend --model [name] --ctx [val]
        if len(sys.argv) < 5:
            print("❌ Error: Missing arguments for recommend.")
            print("Usage: python3 typhon.py recommend --model [name] --ctx [val]")
            sys.exit(1)
        
        # Simple parser for the args
        args_dict = {}
        for i in range(2, len(sys.argv)):
            if sys.argv[i].startswith("--"):
                key = sys.argv[i][2:]
                if i + 1 < len(sys.argv):
                    args_dict[key] = sys.argv[i+1]
        
        if "model" not in args_dict or "ctx" not in args_dict:
            print("❌ Error: Both --model and --ctx are required.")
            sys.exit(1)

        print(f"🔮 [TYPHON] Consulting the Oracle for {args_dict['model']} at {args_dict['ctx']} tokens...")
        subprocess.run(["python3", ORACLE_PATH, "--recommend", "--model", args_dict['model'], "--ctx", args_dict['ctx']])

    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: run, sync, view, train, recommend")
        sys.exit(1)

if __name__ == "__main__":
    main()
