const { Document, Packer } = require('docx')
const { bodyText, bulletItem, dataTable, figureGrid, sectionHeading, titlePage } = require('../templates/shared')

// Usable width of an A4 page with 1-inch margins, in twentieths of a point.
const TABLE_TWIPS = 9000
// Two evidence figures side by side: 3.125 in columns, images 2.9 in wide.
const FIGURE_COLUMN_TWIPS = TABLE_TWIPS / 2
const FIGURE_IMAGE_PX = 280

function blockToDocx(block) {
  if (block.type === 'p') return [bodyText(block.text)]
  if (block.type === 'list') return block.items.map((item) => bulletItem(item))
  if (block.type === 'table') {
    const total = block.widths.reduce((a, b) => a + b, 0)
    const widths = block.widths.map((w) => Math.round((w / total) * TABLE_TWIPS))
    return [dataTable(block.headers, block.rows, widths), bodyText('')]
  }
  if (block.type === 'figures') return [figureGrid(block.items, FIGURE_COLUMN_TWIPS, FIGURE_IMAGE_PX), bodyText('')]
  throw new Error(`Unknown block type ${block.type}`)
}

async function renderDocx(model) {
  const children = [
    ...titlePage(model.title, model.subtitle, model.meta),
    ...model.sections.flatMap((section) => [
      sectionHeading(section.heading, section.level ?? 1),
      ...section.blocks.flatMap(blockToDocx),
    ]),
  ]
  const doc = new Document({ sections: [{ properties: {}, children }] })
  return Packer.toBuffer(doc)
}

module.exports = { renderDocx }
