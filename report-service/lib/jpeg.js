// Start-of-frame markers carry the image size; DHT (C4), JPG (C8) and DAC (CC) do not.
const SOF = new Set([0xc0, 0xc1, 0xc2, 0xc3, 0xc5, 0xc6, 0xc7, 0xc9, 0xca, 0xcb, 0xcd, 0xce, 0xcf])
// Markers without a length field.
const STANDALONE = new Set([0x01, 0xd0, 0xd1, 0xd2, 0xd3, 0xd4, 0xd5, 0xd6, 0xd7, 0xd8, 0xd9])

/**
 * Width and height of a JPEG from its frame header, or null if ``data`` is
 * not a readable JPEG. Word needs the size to scale an image without
 * distorting it, and the report service has no image library.
 */
function jpegSize(data) {
  if (!Buffer.isBuffer(data) || data.length < 4 || data[0] !== 0xff || data[1] !== 0xd8) return null
  let i = 2
  while (i + 3 < data.length) {
    if (data[i] !== 0xff) return null
    const marker = data[i + 1]
    if (marker === 0xff) {
      i += 1 // fill byte
      continue
    }
    if (STANDALONE.has(marker)) {
      i += 2
      continue
    }
    const length = data.readUInt16BE(i + 2)
    if (SOF.has(marker)) {
      if (i + 8 >= data.length) return null
      const height = data.readUInt16BE(i + 5)
      const width = data.readUInt16BE(i + 7)
      return width > 0 && height > 0 ? { width, height } : null
    }
    i += 2 + length
  }
  return null
}

module.exports = { jpegSize }
