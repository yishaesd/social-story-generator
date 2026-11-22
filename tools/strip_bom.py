import glob

targets = (
    sorted(glob.glob("content/**/*.json", recursive=True))
    + sorted(glob.glob("src/*.js"))
    + ["index.html", "README.md", "AGENTS.md"]
)
for f in targets:
    try:
        raw = open(f, "rb").read()
    except FileNotFoundError:
        continue
    if raw.startswith(b"\xef\xbb\xbf"):
        open(f, "wb").write(raw[3:])
        print("BOM removed:", f)
print("checked", len(targets), "files")
