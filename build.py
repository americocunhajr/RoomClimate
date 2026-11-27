from pathlib import Path
p=Path(__file__).parent/'web'
h=(p/'index.html').read_text().replace('<link rel="stylesheet" href="style.css">','<style>'+ (p/'style.css').read_text()+'</style>')
for f in ['solar.js','core.js','app.js','uncertainty.js']: h=h.replace(f'<script src="{f}"></script>','<script>'+ (p/f).read_text()+'</script>')
(p.parent/'RoomClimate.html').write_text(h)

(p.parent/'index.html').write_text(h)
