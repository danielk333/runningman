import pathlib

root = pathlib.Path(__file__).parent.parent
docs = root / "docs"
examples = docs / "examples"


def add_tree(base, folder):
    for file in sorted(folder.rglob("*.py")):
        example_path = file.relative_to(docs)

        if file.parent.name.startswith("."):
            continue
        if file.name.startswith("_wip"):
            continue

        base.append(f"    - {file.stem}: {str(example_path)}")


base = ["  - Examples:", "    - examples/index.md"]
add_tree(base, examples)


print("\n".join(base))
