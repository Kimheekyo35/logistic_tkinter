from flask import Flask, send_file, abort, render_template_string
from datetime import datetime
import tempfile
import shutil
import os

dt = datetime.now()
KST = dt.strftime("%Y_%m_%d")
app = Flask(__name__)

BASE_DIR = "/home/linuxuser/wemarketing/logistic_streamlit"

# fwee, numbuzin 나눠서  다운로드 받을 수 있게
PAGE = """
<!doctype html>
<html>
  <head><meta charset="utf-8"><title>파일 다운로드</title></head>
  <body style="font-family:system-ui; padding:24px;">
    <h2>파일 다운로드</h2>
    <p>아래에서 원하는 브랜드를 선택하세요.</p>

    <div style="display:flex; gap:20px;">
      <a href="/download/fwee" style="display:inline-block;padding:14px 18px;background:#ff5c8a;color:#fff;text-decoration:none;border-radius:12px;">
        fwee 다운로드
      </a>
      <a href="/download/numbuzin" style="display:inline-block;padding:14px 18px;background:#222;color:#fff;text-decoration:none;border-radius:12px;">
        numbuzin 다운로드
      </a>
    </div>
  </body>
</html>
"""

def find_item(brand: str) -> str | None:
    for name in os.listdir(BASE_DIR):
        if brand in name.upper() and KST in name:
            return os.path.join(BASE_DIR, name)
    return None

# 켜자마자 나오는 페이지
@app.get("/")
def home():
    return render_template_string(PAGE)

@app.get("/download/<brand>")
def download_brand(brand:str):
    brand_upper = brand.upper()
    if brand_upper in ("fwee","numbuzin"):
        abort(404)
    path = find_item(brand_upper)
    if not path:
        abort(404, description=f"{brand_upper} + {KST} 항목을 찾지 못했습니다.")

    if os.path.isdir(path):
        tmpdir = tempfile.mkdtemp()
        zip_base = os.path.join(tmpdir, os.path.basename(path))
        zip_path = shutil.make_archive(zip_base,"zip",path)
        return send_file(zip_path,as_attachment=True, download_name=f"{os.path.basename(path)}.zip")
    
    abort(404 )
    
if __name__ == "__main__":
    app.run(host="141.164.49.115", port = 5000)