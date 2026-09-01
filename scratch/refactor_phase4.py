import glob, os, re

files = sorted(glob.glob("backend/analysis/phase4_*.py"))
for f in files:
    with open(f, "r") as file:
        content = file.read()
    
    # Check if we can find def main():
    if "def main():" not in content:
        continue
    
    name = os.path.basename(f).replace(".py", "")
    func_name = "run_" + name.split("_", 2)[2] if "_" in name else "run_" + name
    if "11_12" in name: func_name = "run_reporting"
    
    new_content = content.replace("def main():", f"def {func_name}(run_id=\"run_latest\"):\n    db_path = \"data/discovery_pulse.db\"")
    
    # regex to remove local run_id
    new_content = re.sub(r'run_id\s*=\s*f?["\']run_\{int\(time\.time\(\)\)\}\s*["\']\n', "", new_content)
    new_content = re.sub(r'run_id\s*=\s*f?["\']run_\{?int\(time\.time\(\)\)\}?["\']\n', "", new_content)
    
    # use passed run_id
    new_content = new_content.replace("    passed = main()", f"    passed = {func_name}()")
    new_content = new_content.replace("    main()", f"    {func_name}()")
    
    # Fix DB_PATH references to use the db_path if needed, actually we just leave DB_PATH alone for now
    
    with open(f, "w") as file:
        file.write(new_content)
    print(f"Updated {f} -> {func_name}")
