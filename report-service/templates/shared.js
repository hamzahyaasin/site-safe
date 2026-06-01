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

function formatDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return String(iso)
  }
}

function formatLabel(value) {
  return String(value ?? '—').replace(/_/g, ' ')
}

function filterByDateRange(items, dateFrom, dateTo, field = 'timestamp') {
  const start = new Date(`${dateFrom}T00:00:00`)
  const end = new Date(`${dateTo}T23:59:59.999`)

  return items.filter((item) => {
    const raw = item[field]
    if (!raw) return false
    const date = new Date(raw)
    return date >= start && date <= end
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
  formatDate,
  formatLabel,
  filterByDateRange,
}
