import { Fragment } from 'react'
import { cn } from '../../lib/utils.js'
import EmptyState from './EmptyState.jsx'
import { SkeletonTable } from './Skeleton.jsx'

export default function DataTable({
  columns,
  data,
  loading,
  emptyTitle = 'No data',
  emptyDescription,
  rowKey = (row) => row.id,
  rowClassName,
  expandedRowId,
  renderExpanded,
  onRowClick,
}) {
  if (loading) {
    return (
      <div className="rounded-lg border border-zinc-800 bg-[#151821] p-4">
        <SkeletonTable rows={6} cols={columns.length} />
      </div>
    )
  }

  if (!data?.length) {
    return (
      <EmptyState
        title={emptyTitle}
        description={emptyDescription}
        className="border-zinc-800 bg-[#151821]"
      />
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-zinc-800 bg-[#151821]">
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full min-w-[720px] border-collapse text-left text-sm">
          <thead className="sticky top-0 z-10 bg-zinc-900/95 backdrop-blur-sm">
            <tr className="border-b border-zinc-800">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className={cn(
                    'px-4 py-2.5 text-xs font-medium uppercase tracking-wide text-zinc-500',
                    col.className,
                  )}
                  style={col.width ? { width: col.width } : undefined}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, idx) => {
              const key = rowKey(row, idx)
              const expanded = expandedRowId === key
              return (
                <Fragment key={key}>
                  <tr
                    className={cn(
                      'border-b border-zinc-800/60 transition-colors hover:bg-zinc-800/30',
                      onRowClick && 'cursor-pointer',
                      typeof rowClassName === 'function' ? rowClassName(row) : rowClassName,
                    )}
                    onClick={onRowClick ? () => onRowClick(row) : undefined}
                  >
                    {columns.map((col) => (
                      <td key={col.key} className={cn('px-4 py-2.5 text-zinc-300', col.cellClassName)}>
                        {col.render ? col.render(row, idx) : row[col.key]}
                      </td>
                    ))}
                  </tr>
                  {expanded && renderExpanded ? (
                    <tr key={`${key}-expanded`} className="bg-zinc-900/50">
                      <td colSpan={columns.length} className="px-4 py-4">
                        {renderExpanded(row)}
                      </td>
                    </tr>
                  ) : null}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
