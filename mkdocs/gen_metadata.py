import os
import json
import mkdocs_gen_files
import yaml

# Load list of Markdown file paths from JSON
with open("paths.json", "r") as f:
    pages = json.load(f)

metadata_list = []

for page in pages:
    file_path = page["path"]

    if not os.path.exists(file_path):
        print(f"⚠️ Warning: {file_path} not found, skipping...")
        continue

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Extract metadata from YAML front matter (first lines of the file)
    metadata = {}
    if lines[0].strip() == "---":  # Check if YAML front matter exists
        yaml_content = []
        for line in lines[1:]:
            if line.strip() == "---":
                break
            yaml_content.append(line)
        metadata = yaml.safe_load("\n".join(yaml_content)) or {}

    metadata_list.append({
        "link": file_path.replace("./mkdocs", ".").removesuffix(".md") + "/",
        "title": metadata.get("title", "No Title"),
        "logo": metadata.get("logo", " "),
        "tags": metadata.get("tags", []),
        "description": metadata.get("description", "No Description")
    })

# Save extracted metadata as JSON
with mkdocs_gen_files.open("fetched_metadata.json", "w") as f:
    json.dump(metadata_list, f, indent=2)

print("✅ Metadata extracted and saved to fetched_metadata.json")
