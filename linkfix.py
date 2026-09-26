from pathlib import Path

root = Path(r'C:/Users/slick/dugnictravelsandexpeditions.com')
html_files = list(root.rglob('*.html'))
replacements = {
    'href="../index.html"': 'href="/"',
    'href="./index.html"': 'href="/tours"',
    'href="index.html"': 'href="/"',
    'href="../tours/index.html"': 'href="/tours"',
    'href="tours/index.html"': 'href="/tours"',
    'href="../Contact/index.html"': 'href="/contact"',
    'href="Contact/index.html"': 'href="/contact"',
    'href="../kenya/index.html"': 'href="/kenya"',
    'href="../tanzania/index.html"': 'href="/tanzania"',
    'href="../rwanda/index.html"': 'href="/rwanda"',
    'href="../zanzibar/index.html"': 'href="/zanzibar"',
    'href="../south-africa/index.html"': 'href="/south-africa"',
    'href="../france/index.html"': 'href="/france"',
    'href="../germany/index.html"': 'href="/germany"',
    'href="../thailand/index.html"': 'href="/thailand"',
    'href="../london/index.html"': 'href="/london"',
    'href="../uganda/index.html"': 'href="/uganda"',
}
updated = []
for file in html_files:
    text = file.read_text(encoding='utf-8')
    new_text = text
    for old, new in replacements.items():
        new_text = new_text.replace(old, new)
    if new_text != text:
        file.write_text(new_text, encoding='utf-8')
        updated.append(str(file))
print(f'updated {len(updated)} files')
for path in updated:
    print(path)
