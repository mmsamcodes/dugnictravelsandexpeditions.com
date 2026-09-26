from pathlib import Path
root = Path(r'C:/Users/slick/dugnictravelsandexpeditions.com')
html_files = list(root.rglob('*.html'))
replacements = {
    # root site linking into the English section
    'href="en/index.html"': 'href="/en/"',
    'href="en/tours/index.html"': 'href="/en/tours/"',
    'href="en/Contact/index.html"': 'href="/en/Contact/"',
    # English section navigation
    'href="../index.html"': 'href="/en/"',
    'href="../tours/index.html"': 'href="/en/tours/"',
    'href="../Contact/index.html"': 'href="/en/Contact/"',
    'href="./index.html"': 'href="/en/tours/"',
    # destination links in the tours page
    'href="../kenya/index.html"': 'href="/en/kenya/"',
    'href="../tanzania/index.html"': 'href="/en/tanzania/"',
    'href="../rwanda/index.html"': 'href="/en/rwanda/"',
    'href="../zanzibar/index.html"': 'href="/en/zanzibar/"',
    'href="../south-africa/index.html"': 'href="/en/south-africa/"',
    'href="../france/index.html"': 'href="/en/france/"',
    'href="../germany/index.html"': 'href="/en/germany/"',
    'href="../thailand/index.html"': 'href="/en/thailand/"',
    'href="../london/index.html"': 'href="/en/london/"',
    'href="../uganda/index.html"': 'href="/en/uganda/"',
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
