'use client'
import { useState } from 'react'


export default function DownloadForm() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')


  const handleDownload = () => {
    if (!url) return setError('Please enter a YouTube URL')
    setError('')
    setLoading(true)
    // Trigger browser download
    window.location.href = `/api/download?url=${encodeURIComponent(url)}`
    setTimeout(() => setLoading(false), 1500)
  }


  return (
    <div className="flex flex-col gap-3">
      <input
        className="border p-2 rounded"
        placeholder="https://www.youtube.com/watch?v=..."
        value={url}
        onChange={(e) => setUrl(e.target.value)}
      />


      <div className="flex gap-2">
        <button
          disabled={loading}
          onClick={handleDownload}
          className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-60"
        >
          {loading ? 'Preparing...' : 'Download'}
        </button>
        <button
          onClick={() => setUrl('')}
          className="border px-3 py-2 rounded"
        >
          Clear
        </button>
      </div>


      {error && <p className="text-red-600">{error}</p>}
    </div>
  )
}
