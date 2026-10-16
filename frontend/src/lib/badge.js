import QRCode from 'qrcode'

function escapeHtml(text) {
  return String(text ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c])
}

/** Open a print-ready worker badge. The QR encodes only the badge payload
 * (a random code), never the worker's name or phone number. Print at
 * 100% scale: the code is 60 mm square, the size the camera tests assume. */
export async function printBadge({ name, role, payload }) {
  const svg = await QRCode.toString(payload, { type: 'svg', errorCorrectionLevel: 'M', margin: 2 })
  const win = window.open('', '_blank', 'width=480,height=640')
  if (!win) throw new Error('Allow pop-ups for this site to print badges.')
  win.document.write(`<!doctype html>
<html><head><meta charset="utf-8"><title>Badge – ${escapeHtml(name)}</title>
<style>
  @page { size: 86mm 120mm; margin: 6mm; }
  body { font-family: Arial, sans-serif; text-align: center; margin: 0; color: #000; background: #fff; }
  .qr svg { width: 60mm; height: 60mm; }
  h1 { font-size: 16pt; margin: 4mm 0 1mm; }
  p { margin: 0; font-size: 10pt; }
  .note { margin-top: 4mm; font-size: 7pt; color: #444; }
</style></head>
<body>
  <p><strong>SITE-SAFE</strong></p>
  <div class="qr">${svg}</div>
  <h1>${escapeHtml(name)}</h1>
  <p>${escapeHtml(role || '')}</p>
  <p class="note">Wear on the front of the helmet or chest, unobstructed.</p>
</body></html>`)
  win.document.close()
  win.focus()
  win.setTimeout(() => win.print(), 300)
}
