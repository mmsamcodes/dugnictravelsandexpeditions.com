from pathlib import Path
root = Path(r'C:/Users/slick/dugnictravelsandexpeditions.com/en')
files = list(root.rglob('*.html'))
replacements = {
    'href="../index.html"': 'href="/en/index.html"',
    'href="../tours/index.html"': 'href="/en/tours/index.html"',
    'href="./index.html"': 'href="/en/tours/index.html"',
    'href="../Contact/index.html"': 'href="/en/Contact/index.html"',
    'href="../kenya/index.html"': 'href="/en/kenya/index.html"',
    'href="../tanzania/index.html"': 'href="/en/tanzania/index.html"',
    'href="../rwanda/index.html"': 'href="/en/rwanda/index.html"',
    'href="../zanzibar/index.html"': 'href="/en/zanzibar/index.html"',
    'href="../south-africa/index.html"': 'href="/en/south-africa/index.html"',
    'href="../france/index.html"': 'href="/en/france/index.html"',
    'href="../germany/index.html"': 'href="/en/germany/index.html"',
    'href="../thailand/index.html"': 'href="/en/thailand/index.html"',
    'href="../london/index.html"': 'href="/en/london/index.html"',
    'href="../uganda/index.html"': 'href="/en/uganda/index.html"',
}
updated = []
for file in files:
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
