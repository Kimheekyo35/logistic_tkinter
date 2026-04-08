import base64
from playwright.sync_api import Page
from pathlib import Path
def download_pdf_from_shopee_preview(
    page: Page,
    save_path: str,
    stable_wait_ms: int = 30000,
) -> str:
    iframe = page.locator("iframe[type='application/pdf'][src^='blob:'], iframe[src^='blob:']").first
    iframe.wait_for(state="attached", timeout=60000)

    page.wait_for_function("""
      () => {
        const f = document.querySelector("iframe[src^='blob:']");
        return !!f && typeof f.getAttribute("src") === "string" && f.getAttribute("src").startsWith("blob:");
      }
    """, timeout=60000)

    # PDF가 떠도 추가 안정화 대기
    page.wait_for_timeout(stable_wait_ms)

    js = r"""
    async () => {
      const f = document.querySelector("iframe[src^='blob:']");
      if (!f) throw new Error("blob iframe 없음");

      const blobUrl = (f.getAttribute("src") || "").split("#")[0];
      const res = await fetch(blobUrl);
      if (!res.ok) throw new Error("fetch 실패: " + res.status);

      const blob = await res.blob();
      const buf = await blob.arrayBuffer();

      let binary = "";
      const bytes = new Uint8Array(buf);
      const chunkSize = 0x8000;
      for (let i = 0; i < bytes.length; i += chunkSize) {
        binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
      }

      return {
        b64: btoa(binary),
        type: blob.type || "",
        size: blob.size
      };
    }
    """

    result = page.evaluate(js)

    out = Path(save_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(result["b64"]))

    return str(out)