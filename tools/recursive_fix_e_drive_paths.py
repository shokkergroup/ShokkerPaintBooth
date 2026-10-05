import os
import re

TARGET_DIR = r"C:\DRIVE E BACKUP\Shokker Paint Booth Gold to Platinum"
EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".vscode", ".claude"}
VALID_EXTENSIONS = {".json", ".md", ".html", ".js", ".py", ".yml", ".yaml", ".txt", ".bat", ".vbs", ".sh"}

stale_patterns = [
    ("C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum", "C:/DRIVE E BACKUP/Shokker Paint Booth Gold to Platinum"),
    ("C:\\DRIVE E BACKUP\\Shokker Paint Booth Gold to Platinum", "C:\\DRIVE E BACKUP\\Shokker Paint Booth Gold to Platinum"),
    ("C:/DRIVE E BACKUP", "C:/DRIVE E BACKUP"),
    ("C:\\DRIVE E BACKUP", "C:\\DRIVE E BACKUP"),
]

print("Starting recursive replacement of stale E: drive paths in all text files...")
updated_count = 0

for root, dirs, files in os.walk(TARGET_DIR):
    # Prune excluded directories in place
    dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
    
    for file in files:
        _, ext = os.path.splitext(file)
        if ext.lower() not in VALID_EXTENSIONS:
            continue
            
        full_path = os.path.join(root, file)
        
        try:
            with open(full_path, "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
                
            has_change = False
            new_content = content
            for old, new in stale_patterns:
                insensitive_old = re.compile(re.escape(old), re.IGNORECASE)
                new_content, count = insensitive_old.subn(lambda m, replacement=new: replacement, new_content)
                if count > 0:
                    has_change = True
                    
            if has_change:
                with open(full_path, "w", encoding="utf-8") as fh:
                    fh.write(new_content)
                # print relative path
                rel_path = os.path.relpath(full_path, TARGET_DIR)
                print(f"[+] Updated: {rel_path}")
                updated_count += 1
                
        except Exception as exc:
            print(f"[-] Error checking/updating {file}: {exc}")

print(f"Recursive replacement complete! Updated {updated_count} files successfully.")
