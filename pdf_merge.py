from PyPDF2 import PdfReader, PdfWriter
from pathlib import Path
import re


def pdf_merge(folder_path:str, country:str, chunk_pages: int = 1200):
    folder = Path(folder_path)
    folder.mkdir(parents=True, exist_ok=True)

    # numbuzin_{country}_YYYY_MM_DD_HHMMSS.pdf 에 맞는 것만
    pattern = re.compile(rf"^NUMBUZIN_{re.escape(country)}_\d{{4}}_\d{{2}}_\d{{2}}_\d+\.pdf$", re.IGNORECASE)

    pdfs = sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".pdf" and pattern.match(p.name)])

    if not pdfs:
            print(f"[{country}] 병합할 PDF가 없습니다: {folder}")
            return

    writer = PdfWriter()
    part = 1
    page_count = 0

    base_folder_name = folder.name  # 예: NUMBUZIN_2026_02_25

    def flush():
        nonlocal writer, part, page_count
        out_path = folder / f"{base_folder_name}_{country}_merged_{part}.pdf"
        with open(out_path, "wb") as f:
            writer.write(f)
        print(f"[{country}] 생성 완료: {out_path}")
        part += 1
        writer = PdfWriter()
        page_count = 0

    for pdf_path in pdfs:
        reader = PdfReader(str(pdf_path))
        for page in reader.pages:
            writer.add_page(page)
            page_count += 1
            if page_count == chunk_pages:
                flush()

    if page_count > 0:
        flush()
    
    return (f"{country}_병합 완료")

country_list = ["Vietnam","TaiwanXiapi"]
for country in country_list:
    pdf_merge("C:/Users/suppo/OneDrive/Desktop/물류/NUMBUZIN_2026_02_26_1",country,1200)