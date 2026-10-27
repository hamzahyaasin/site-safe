const PDFDocument = require('pdfkit')

const MARGIN = 72 // 1 inch
const FONT = 'Times-Roman'
const BOLD = 'Times-Bold'
const ITALIC = 'Times-Italic'
const CELL_PAD = 4
const BODY = 11
const CELL = 8.5

// The built-in PDF fonts use WinAnsi encoding; map the few other characters
// the templates can produce so nothing renders as garbage.
const REPLACEMENTS = { '→': '->', '∞': 'unlimited', '≥': '>=', '≤': '<=', '✓': 'yes' }
function pdfSafe(text) {
  return String(text ?? '')
    .replace(/[→∞≥≤✓]/g, (c) => REPLACEMENTS[c])
    .replace(/[^\x09\x0A\x0D\x20-\x7E -ÿ–—‘’“”•…]/g, '?')
}

function bottom(doc) {
  return doc.page.height - doc.page.margins.bottom
}

function ensureSpace(doc, height) {
  if (doc.y + height > bottom(doc)) doc.addPage()
}

function drawTable(doc, { headers, rows, widths }) {
  const usable = doc.page.width - doc.page.margins.left - doc.page.margins.right
  const total = widths.reduce((a, b) => a + b, 0)
  const cols = widths.map((w) => (w / total) * usable)
  const left = doc.page.margins.left

  const rowHeight = (cells, font) => {
    doc.font(font).fontSize(CELL)
    return Math.max(
      ...cells.map((c, i) => doc.heightOfString(pdfSafe(c), { width: cols[i] - CELL_PAD * 2 })),
    ) + CELL_PAD * 2
  }

  const drawRow = (cells, font, shade) => {
    const h = rowHeight(cells, font)
    const top = doc.y
    let x = left
    cells.forEach((cell, i) => {
      if (shade) doc.rect(x, top, cols[i], h).fillAndStroke('#e8e8e8', '#999999')
      else doc.rect(x, top, cols[i], h).stroke('#999999')
      doc.fillColor('#000000').font(font).fontSize(CELL)
      doc.text(pdfSafe(cell), x + CELL_PAD, top + CELL_PAD, { width: cols[i] - CELL_PAD * 2 })
      x += cols[i]
    })
    doc.x = left
    doc.y = top + h
  }

  doc.lineWidth(0.5)
  ensureSpace(doc, rowHeight(headers, BOLD) + rowHeight(rows[0] ?? headers, FONT))
  drawRow(headers, BOLD, true)
  for (const row of rows) {
    // Repeat the header on every page the table continues onto.
    if (doc.y + rowHeight(row, FONT) > bottom(doc)) {
      doc.addPage()
      drawRow(headers, BOLD, true)
    }
    drawRow(row, FONT, false)
  }
  doc.moveDown(0.8)
}

const FIGURE_GAP = 14
const CAPTION = 8

/** Evidence figures two to a row, each image the column's width, captioned underneath. */
function drawFigures(doc, { items }) {
  const left = doc.page.margins.left
  const usable = doc.page.width - left - doc.page.margins.right
  const col = (usable - FIGURE_GAP) / 2

  const captionHeight = (item) => {
    let h = 0
    item.caption.forEach((line, i) => {
      doc.font(i === 0 ? BOLD : FONT).fontSize(CAPTION)
      h += doc.heightOfString(pdfSafe(line), { width: col })
    })
    return h
  }
  const figureHeight = (item) => (col * item.height) / item.width + 4 + captionHeight(item)

  for (let i = 0; i < items.length; i += 2) {
    const pair = items.slice(i, i + 2)
    const rowHeight = Math.max(...pair.map(figureHeight))
    ensureSpace(doc, rowHeight)
    const top = doc.y
    pair.forEach((item, j) => {
      const x = left + j * (col + FIGURE_GAP)
      const imageHeight = (col * item.height) / item.width
      doc.image(item.image, x, top, { width: col, height: imageHeight })
      doc.rect(x, top, col, imageHeight).lineWidth(0.5).stroke('#999999')
      let y = top + imageHeight + 4
      item.caption.forEach((line, k) => {
        doc.fillColor('#000000').font(k === 0 ? BOLD : FONT).fontSize(CAPTION)
        doc.text(pdfSafe(line), x, y, { width: col })
        y = doc.y
      })
    })
    doc.x = left
    doc.y = top + rowHeight + 12
  }
  doc.moveDown(0.4)
}

function renderPdf(model) {
  return new Promise((resolve, reject) => {
    const doc = new PDFDocument({
      size: 'A4',
      margins: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN },
      bufferPages: true,
      info: { Title: model.title, Producer: 'Site-Safe report service' },
    })
    const chunks = []
    doc.on('data', (c) => chunks.push(c))
    doc.on('end', () => resolve(Buffer.concat(chunks)))
    doc.on('error', reject)

    try {
      doc.font(BOLD).fontSize(22).text(pdfSafe(model.title), { align: 'center' })
      doc.moveDown(0.3)
      doc.font(ITALIC).fontSize(13).text(pdfSafe(model.subtitle), { align: 'center' })
      doc.moveDown(0.8)
      doc.font(FONT).fontSize(BODY)
      for (const line of model.meta) doc.text(pdfSafe(line), { align: 'center' })
      doc.moveDown(1.5)

      for (const section of model.sections) {
        ensureSpace(doc, 60)
        doc.font(BOLD).fontSize(section.level === 2 ? 13 : 15).text(pdfSafe(section.heading))
        doc.moveDown(0.4)
        for (const block of section.blocks) {
          if (block.type === 'p') {
            doc.font(FONT).fontSize(BODY).text(pdfSafe(block.text), { align: 'justify' })
            doc.moveDown(0.6)
          } else if (block.type === 'list') {
            doc.font(FONT).fontSize(BODY)
            for (const item of block.items) {
              doc.text(pdfSafe(`• ${item}`), { indent: 10, align: 'justify' })
              doc.moveDown(0.25)
            }
            doc.moveDown(0.4)
          } else if (block.type === 'table') {
            drawTable(doc, block)
          } else if (block.type === 'figures') {
            drawFigures(doc, block)
          }
        }
      }

      const range = doc.bufferedPageRange()
      for (let i = range.start; i < range.start + range.count; i += 1) {
        doc.switchToPage(i)
        // Writing inside the bottom margin would otherwise start a new page.
        const savedBottom = doc.page.margins.bottom
        doc.page.margins.bottom = 0
        doc.font(FONT).fontSize(9).fillColor('#555555')
        doc.text(`Page ${i + 1} of ${range.count}`, MARGIN, doc.page.height - MARGIN / 2, {
          width: doc.page.width - MARGIN * 2,
          align: 'center',
          lineBreak: false,
        })
        doc.page.margins.bottom = savedBottom
      }
      doc.end()
    } catch (error) {
      reject(error)
    }
  })
}

module.exports = { renderPdf, pdfSafe }
