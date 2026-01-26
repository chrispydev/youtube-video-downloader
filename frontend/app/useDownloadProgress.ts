import { useEffect, useRef, useState } from "react";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export type StartOpts = {
  url: string;
  formatId: string;
  subtitleLang?: string | null;
  filename?: string | null;
};

export type ProgressState = {
  downloadId: string | null;
  progress: number | null;
  speed: number | null; // bytes/sec
  eta: number | null; // seconds
  status: string | null;
  downloading: boolean;
};

export default function useDownloadProgress() {
  const [downloadId, setDownloadId] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [speed, setSpeed] = useState<number | null>(null);
  const [eta, setEta] = useState<number | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    return () => {
      if (esRef.current) {
        try {
          esRef.current.close();
        } catch (e) {
          // ignore
        }
        esRef.current = null;
      }
    };
  }, []);

  async function start(opts: StartOpts): Promise<string | null> {
    const { url, formatId, subtitleLang, filename } = opts;
    setDownloading(true);
    setProgress(0);
    setSpeed(null);
    setEta(null);
    setStatus("Starting download...");

    try {
      const res = await fetch(`${BACKEND}/download`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          format_id: formatId,
          subtitle_lang: subtitleLang ?? null,
        }),
      });

      if (!res.ok) {
        const err = await res.text();
        setStatus(`❌ Failed to start download: ${err}`);
        setDownloading(false);
        return null;
      }

      const body = await res.json();
      const id = body.download_id as string;
      setDownloadId(id);

      // ensure previous eventsource closed
      if (esRef.current) {
        try {
          esRef.current.close();
        } catch (e) {
          // ignore
        }
        esRef.current = null;
      }

      const es = new EventSource(`${BACKEND}/progress/${id}`);
      esRef.current = es;

      es.onmessage = async (ev) => {
        let data: any = null;
        try {
          data = JSON.parse(ev.data);
        } catch (e) {
          // ignore invalid messages
          return;
        }

        setStatus(data.status ?? null);

        if (typeof data.progress === "number") setProgress(data.progress);
        if (typeof data.speed === "number") setSpeed(data.speed);
        if (typeof data.eta === "number") setEta(data.eta);

        if (data.status === "error" || data.error) {
          setStatus(`❌ ${data.error ?? "error"}`);
          setDownloading(false);
          if (esRef.current) {
            try {
              esRef.current.close();
            } catch (e) {}
            esRef.current = null;
          }
        }

        if (data.finished || data.status === "finished") {
          setProgress(100);
          setStatus("Finalizing file...");
          if (esRef.current) {
            try {
              esRef.current.close();
            } catch (e) {}
            esRef.current = null;
          }

          // fetch file and trigger download
          try {
            const fileRes = await fetch(`${BACKEND}/download/${id}/file`);
            if (!fileRes.ok) {
              const errBody = await fileRes.text();
              throw new Error(errBody || "Failed to fetch file");
            }
            const blob = await fileRes.blob();
            const fn =
              filename ??
              (data.title
                ? `${(data.title as string).replace(/[^\w\s-]/g, "")}.mp4`
                : `video_${id}.mp4`);
            const urlBlob = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = urlBlob;
            a.download = fn;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(urlBlob);
            setStatus("✅ Download complete!");
          } catch (err: any) {
            setStatus(`❌ Error fetching file: ${err?.message ?? err}`);
          } finally {
            setDownloading(false);
          }
        }
      };

      es.onerror = (err) => {
        setStatus("Connection lost to progress stream");
        setDownloading(false);
        if (esRef.current) {
          try {
            esRef.current.close();
          } catch (e) {}
          esRef.current = null;
        }
      };

      return id;
    } catch (err: any) {
      setStatus(`❌ Error starting download: ${err?.message ?? err}`);
      setDownloading(false);
      return null;
    }
  }

  async function cancel(): Promise<boolean> {
    if (!downloadId) return false;
    try {
      const res = await fetch(`${BACKEND}/download/${downloadId}/cancel`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.text();
        setStatus(`❌ Cancel failed: ${err}`);
        return false;
      }
      setStatus("Cancelled");
      setDownloading(false);
      if (esRef.current) {
        try {
          esRef.current.close();
        } catch (e) {}
        esRef.current = null;
      }
      return true;
    } catch (err: any) {
      setStatus(`❌ Cancel error: ${err?.message ?? err}`);
      return false;
    }
  }

  return {
    // state
    downloadId,
    progress,
    speed,
    eta,
    status,
    downloading,
    // actions
    start,
    cancel,
  } as const;
}
