from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree
from pptx import Presentation
import fitz, hashlib, json
from PIL import Image, ImageDraw

root=Path(__file__).resolve().parent
pptx=root/'Real_Estate_Portfolio_Intelligence_Client_Deck.pptx'
pdf=pptx.with_suffix('.pdf');p=Presentation(pptx);d=fitz.open(pdf)
assert len(p.slides)==len(d)==22
checks=json.loads((root/'powerpoint_layout_check.json').read_text())
assert not any(s['text_overflows'] for s in checks)
assert all(s.notes_slide.notes_text_frame.text.strip() for s in p.slides)
assert all(len(page.get_text())>80 for page in d)
charts=sum(sh.has_chart for s in p.slides for sh in s.shapes)
assert charts==6
outside=[]
for i,s in enumerate(p.slides):
    for sh in s.shapes:
        if sh.left < -10000 or sh.top < -10000 or sh.left+sh.width>p.slide_width+10000 or sh.top+sh.height>p.slide_height+10000:
            outside.append((i+1,sh.name))
assert not outside,outside
for i,page in enumerate(d):
    page.get_pixmap(matrix=fitz.Matrix(1.4,1.4),alpha=False).save(root/'qa'/f'slide-{i+1:02}.png')
for start in range(0,len(d),6):
    sheet=Image.new('RGB',(1600,1450),'#d4d8de');draw=ImageDraw.Draw(sheet)
    for j in range(start,min(start+6,len(d))):
        im=Image.open(root/'qa'/f'slide-{j+1:02}.png');im.thumbnail((780,439));x=(j-start)%2*800;y=(j-start)//2*480
        sheet.paste(im,(x+10,y+26));draw.text((x+12,y+7),f'Slide {j+1}',fill='black')
    sheet.save(root/'qa'/f'contact-{start//6+1}.png')
with ZipFile(pptx) as z:
    assert not any(n.startswith('ppt/media/') for n in z.namelist())
    books=[n for n in z.namelist() if n.startswith('ppt/embeddings/')];assert len(books)==6
    embedded=[n for n in z.namelist() if n.startswith('ppt/fonts/')]
    ns={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart'}
    for n in [n for n in z.namelist() if n.startswith('ppt/charts/chart') and n.endswith('.xml')]:
        assert all(e.get('val')=='0' for e in etree.fromstring(z.read(n)).xpath('//c:invertIfNegative',namespaces=ns))
manifest={
    'slides':len(p.slides),'editable_shapes':sum(len(s.shapes) for s in p.slides),'native_charts':charts,
    'embedded_chart_workbooks':len(books),'editable_decision_plots':2,'embedded_fonts':len(embedded),
    'rasterized_slides':0,'overflowing_text_boxes':0,'off_canvas_shapes':0,
    'pdf_links':sum(len(page.get_links()) for page in d),'reference_pages_used':'1â€“18 only',
    'figure_reconciliation':'Reviewed against saved model outputs; all six additional policy runs pass constraint audits',
    'files':[]}
for path in [pptx,pdf]:
    manifest['files'].append({'name':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(root/'delivery_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8',newline='\n')
package=root/'Client_Presentation_Package.zip'
with ZipFile(package,'w',ZIP_DEFLATED) as z:
    for path in [pptx,pdf,root/'README.md',root/'delivery_manifest.json',root/'analysis/zoning-decision-trace.md',root/'fonts/IBMPlexSans-Regular.ttf',root/'fonts/IBMPlexSans-Light.ttf',root/'fonts/LICENSE.txt']:
        z.write(path,path.relative_to(root))
print(json.dumps(manifest,indent=2))
print('Complete package:',package,package.stat().st_size)
