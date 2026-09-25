"""Render through PowerPoint, retain native editing, and validate geometry."""
from pathlib import Path
import ctypes, json, zipfile
import win32com.client

ROOT=Path(__file__).resolve().parent
deck=ROOT/'Portfolio_Intelligence_Demo_Workflows.pptx'
pdf=deck.with_suffix('.pdf')
for font in (ROOT.parent/'client/fonts').glob('*.ttf'):
    ctypes.windll.gdi32.AddFontResourceExW(str(font),0,0)
ctypes.windll.user32.SendMessageTimeoutW(0xffff,0x001D,0,0,2,5000,None)
app=pres=None
try:
    app=win32com.client.DispatchEx('PowerPoint.Application')
    pres=app.Presentations.Open(str(deck),ReadOnly=False,Untitled=False,WithWindow=False)
    try:pres.SaveSubsetFonts=False
    except Exception:pass
    pres.SaveAs(str(deck),24,-1)
    pres.SaveAs(str(pdf),32)
    checks=[]
    for sl in pres.Slides:
        overflowing=[]
        for sh in sl.Shapes:
            if sh.HasTextFrame and sh.TextFrame.HasText:
                tr=sh.TextFrame2.TextRange
                if tr.BoundHeight>sh.Height+2 or tr.BoundWidth>sh.Width+2:
                    overflowing.append({'text':str(tr.Text),'box':[round(sh.Left,1),round(sh.Top,1),round(sh.Width,1),round(sh.Height,1)],'text_bounds':[round(tr.BoundWidth,1),round(tr.BoundHeight,1)]})
        checks.append({'slide':sl.SlideIndex,'text_overflows':overflowing})
    (ROOT/'powerpoint_layout_check.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
finally:
    if pres is not None:pres.Close()
    if app is not None:app.Quit()
with zipfile.ZipFile(deck) as z:embedded=[n for n in z.namelist() if n.startswith('ppt/fonts/')]
print(json.dumps({'pdf':str(pdf),'embedded_fonts':len(embedded),'slides':len(checks),'text_overflows':sum(len(s['text_overflows']) for s in checks)},indent=2))
