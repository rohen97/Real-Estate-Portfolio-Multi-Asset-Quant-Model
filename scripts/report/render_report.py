"""Update the Word report fields and export PDF with local Microsoft Word."""
from pathlib import Path
import hashlib
import json
import shutil

import win32com.client

ROOT = Path(__file__).resolve().parents[2]
target = ROOT / 'docs/reports/Real_Estate_Dashboard_Interpretation_Report.docx'
pdf = target.with_suffix('.pdf')
word = document = None
try:
    word = win32com.client.DispatchEx('Word.Application')
    word.Visible = False
    word.DisplayAlerts = 0
    word.AutomationSecurity = 3
    document = word.Documents.Open(str(target), ReadOnly=False, AddToRecentFiles=False)
    document.Fields.Update()
    document.Repaginate()
    for index in range(1, document.TablesOfContents.Count + 1):
        document.TablesOfContents(index).Update()
    document.Repaginate()
    document.Fields.Update()
    document.Save()
    document.ExportAsFixedFormat(str(pdf), 17, OpenAfterExport=False)
    result = {'pages': document.ComputeStatistics(2), 'words': document.ComputeStatistics(0), 'pdf': str(pdf)}
finally:
    if document is not None:
        document.Close(SaveChanges=False)
    if word is not None:
        word.Quit()

manifest_path = target.parent / 'source_manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
for key, path in [('report', target), ('pdf', pdf)]:
    manifest[key] = {'path': str(path.relative_to(ROOT)).replace('\\', '/'),
                     'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
    shutil.copy2(path, ROOT / 'public/reports' / path.name)
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
print(json.dumps(result, indent=2))
