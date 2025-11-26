import ytdl from 'ytdl-core'
import { PassThrough } from 'stream'


export const runtime = 'nodejs'


export async function GET(request: Request) {
  try {
    const url = new URL(request.url).searchParams.get('url')
    if (!url || !ytdl.validateURL(url)) {
      return new Response(JSON.stringify({ error: 'Invalid or missing url' }), { status: 400 })
    }


    const id = ytdl.getURLVideoID(url)
    const passthrough = new PassThrough()


    // Kick off the ytdl stream and pipe to passthrough
    const stream = ytdl(url, { quality: 'highest' })
    stream.on('error', (err) => {
      try {
        passthrough.destroy(err)
      } catch (e) { }
    })
    stream.pipe(passthrough)


    const headers = new Headers()
    headers.set('Content-Disposition', `attachment; filename="${id}.mp4"`)
    headers.set('Content-Type', 'video/mp4')


    return new Response(passthrough as unknown as ReadableStream<Uint8Array>, { headers })
  } catch (err) {
    return new Response(JSON.stringify({ error: 'Server error' }), { status: 500 })
  }
}
