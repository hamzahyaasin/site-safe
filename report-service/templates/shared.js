const {
  AlignmentType,
  HeadingLevel,
  PageBreak,
  Paragraph,
  TextRun,
  WidthType,
} = require('docx')

const FONT = 'Times New Roman'

const SIZE = {
  title: 56,
  subtitle: 28,
  heading1: 32,
  heading2: 28,
  body: 24,
  small: 20,
}

function run(text, options = {}) {
  return new TextRun({
    text: String(text ?? ''),
    font: FONT,
    size: options.size ?? SIZE.body,
    bold: options.bold ?? false,
    italics: options.italics ?? false,
    color: options.color,
  })
}

function paragraph(children, options = {}) {
  const runs = Array.isArray(children) ? children : [run(children, options)]
  return new Paragraph({
    children: runs,
    alignment: options.alignment,
    heading: options.heading,
    spacing: options.spacing ?? { after: 120 },
  })
}

function titlePage(title, subtitle, metaLines = []) {
  const blocks = [
    paragraph([run(title, { size: SIZE.title, bold: true })], {
      alignment: AlignmentType.CENTER,
      spacing: { before: 2400, after: 240 },
    }),
    paragraph([run(subtitle, { size: SIZE.subtitle, italics: true })], {
      alignment: AlignmentType.CENTER,
      spacing: { after: 480 },
    }),
  ]

  for (const line of metaLines) {
    blocks.push(
      paragraph([run(line, { size: SIZE.body })], {
        alignment: AlignmentType.CENTER,
        spacing: { after: 120 },
      }),
    )
  }

  blocks.push(new Paragraph({ children: [new PageBreak()] }))
  return blocks
}

function sectionHeading(text, level = 1) {
  return paragraph([run(text, { size: level === 1 ? SIZE.heading1 : SIZE.heading2, bold: true })], {
    heading: level === 1 ? HeadingLevel.HEADING_1 : HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 160 },
  })
}

function bodyText(text) {
  return paragraph([run(text)])
}

function bulletItem(text) {
  return new Paragraph({
    children: [run(`• ${text}`)],
    indent: { left: 360 },
    spacing: { after: 80 },
  })
}

function tableCell(text, options = {}) {
  return {
    children: [
      new Paragraph({
        children: [run(text, { size: SIZE.small, bold: options.bold ?? false })],
        spacing: { before: 40, after: 40 },
      }),
    ],
  }
}

const NO_BORDER = { style: 'none', size: 0, color: 'FFFFFF' }
const NO_BORDERS = { top: NO_BORDER, bottom: NO_BORDER, left: NO_BORDER, right: NO_BORDER }

/**
 * Evidence figures two to a row: each image scaled to ``imageWidth`` pixels
 * wide (Word's 96 per inch) keeping its shape, captioned underneath. A row
 * is never split across pages.
 */
function figureGrid(items, columnTwips, imageWidth) {
  const { ImageRun, Table, TableRow, TableCell } = require('docx')

  const cell = (item) =>
    new TableCell({
      borders: NO_BORDERS,
      width: { size: columnTwips, type: WidthType.DXA },
      margins: { top: 80, bottom: 160, left: 60, right: 60 },
      children: item
        ? [
            new Paragraph({
              children: [
                new ImageRun({
                  type: 'jpg',
                  data: item.image,
                  transformation: { width: imageWidth, height: Math.round((imageWidth * item.height) / item.width) },
                  altText: { name: item.label, title: item.label, description: item.alt },
                }),
              ],
              spacing: { after: 60 },
            }),
            ...item.caption.map(
              (line, i) =>
                new Paragraph({
                  children: [run(line, { size: 16, bold: i === 0 })],
                  spacing: { after: 20 },
                }),
            ),
          ]
        : [new Paragraph({ children: [] })],
    })

  const rows = []
  for (let i = 0; i < items.length; i += 2) {
    rows.push(new TableRow({ cantSplit: true, children: [cell(items[i]), cell(items[i + 1])] }))
  }
  return new Table({
    width: { size: columnTwips * 2, type: WidthType.DXA },
    columnWidths: [columnTwips, columnTwips],
    borders: { ...NO_BORDERS, insideHorizontal: NO_BORDER, insideVertical: NO_BORDER },
    rows,
  })
}

function dataTable(headers, rows, columnWidths) {
  const { Table, TableRow, TableCell } = require('docx')

  const headerRow = new TableRow({
    children: headers.map((header) => new TableCell({ ...tableCell(header, { bold: true }) })),
    tableHeader: true,
  })

  const bodyRows = rows.map(
    (row) =>
      new TableRow({
        children: row.map((cell) => new TableCell({ ...tableCell(cell) })),
      }),
  )

  return new Table({
    width: { size: 100, type: WidthType.PERCENTAGE },
    columnWidths,
    rows: [headerRow, ...bodyRows],
  })
}

module.exports = {
  FONT,
  SIZE,
  run,
  paragraph,
  titlePage,
  sectionHeading,
  bodyText,
  bulletItem,
  dataTable,
  figureGrid,
}
