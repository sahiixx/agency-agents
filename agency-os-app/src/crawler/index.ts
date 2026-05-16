import { spawn } from "child_process";

export interface CrawlResult {
  source: string;
  text?: string;
  link?: string;
  title?: string;
  htmlLength?: number;
}

export async function runCrawl(
  url: string,
  selector?: string,
  _engine: string = "auto"
): Promise<{ results: CrawlResult[]; error?: string }> {
  const script = `
import json, sys, time, re
try:
    import requests
    from bs4 import BeautifulSoup
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp = requests.get(${JSON.stringify(url)}, headers=headers, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    if ${JSON.stringify(selector)}:
        for item in soup.select(${JSON.stringify(selector)})[:30]:
            data = {"source": ${JSON.stringify(url)}, "time": time.time()}
            text = item.get_text(strip=True)
            if text: data["text"] = text[:300]
            link = item.find("a")
            if link and link.get("href"): data["link"] = link["href"]
            results.append(data)
    else:
        title = soup.title.string if soup.title else None
        results.append({"source": ${JSON.stringify(url)}, "title": title, "htmlLength": len(resp.text)})
    print(json.dumps({"results": results, "error": None}))
except Exception as e:
    print(json.dumps({"results": [], "error": str(e)}))
`;

  return new Promise((resolve) => {
    const proc = spawn(process.execPath, ["-c", script], { timeout: 60000 });
    let stdout = "";
    proc.stdout.on("data", (d) => (stdout += d.toString()));
    proc.on("close", () => {
      try {
        const out = JSON.parse(stdout.trim().split("\n").pop() || "{}");
        resolve({ results: out.results || [], error: out.error });
      } catch {
        resolve({ results: [], error: "Parse error" });
      }
    });
  });
}
