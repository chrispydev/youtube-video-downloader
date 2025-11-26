import DownloadForm from '@/components/download-form'


export default function Page() {
  return (
    <div>
      <h1 className="text-2xl font-semibold mb-4">Next.js YouTube Downloader</h1>
      <DownloadForm />
      <section className="mt-6 text-sm text-gray-600">
        <p>Tip: Use a short YouTube link or full URL. The server streams the file.</p>
      </section>
    </div>
  )
}
