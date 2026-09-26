from pathlib import Path

root = Path(r'C:/Users/slick/dugnictravelsandexpeditions.com/en')
files = list(root.rglob('*.html'))
replacements = {
    'href="/"': 'href="/en/"',
    'href="/tours"': 'href="/en/tours/"',
    'href="/contact"': 'href="/en/Contact/"',
    'href="/kenya"': 'href="/en/kenya/"',
    'href="/tanzania"': 'href="/en/tanzania/"',
    'href="/rwanda"': 'href="/en/rwanda/"',
    'href="/zanzibar"': 'href="/en/zanzibar/"',
    'href="/south-africa"': 'href="/en/south-africa/"',
    'href="/france"': 'href="/en/france/"',
    'href="/germany"': 'href="/en/germany/"',
    'href="/thailand"': 'href="/en/thailand/"',
    'href="/london"': 'href="/en/london/"',
    'href="/uganda"': 'href="/en/uganda/"',
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
