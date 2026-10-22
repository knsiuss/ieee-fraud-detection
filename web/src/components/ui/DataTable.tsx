import React, { useState } from 'react';
import {
  type ColumnDef,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from '@tanstack/react-table';
import { ChevronDown, ChevronUp, ChevronsUpDown } from 'lucide-react';

interface DataTableProps<TData> {
  columns: ColumnDef<TData, any>[];
  data: TData[];
  onRowClick?: (row: TData) => void;
  selectedRowId?: string;
  idAccessor?: (row: TData) => string;
  emptyMessage?: string;
  /** Render without the outer card (for embedding inside a panel). */
  bare?: boolean;
}

export function DataTable<TData>({
  columns,
  data,
  onRowClick,
  selectedRowId,
  idAccessor,
  emptyMessage = 'No records in ledger.',
  bare = false,
}: DataTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div
      className={
        bare
          ? 'w-full overflow-hidden'
          : 'panel w-full overflow-hidden'
      }
    >
      <div className="max-h-[560px] overflow-x-auto">
        <table className="w-full border-collapse text-left text-xs">
          <thead className="sticky top-0 z-10 border-b border-border-subtle bg-surface-2">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const isSorted = header.column.getIsSorted();

                  return (
                    <th
                      key={header.id}
                      className={`select-none px-4 py-2.5 text-[10.5px] font-semibold uppercase tracking-[0.06em] text-text-muted ${
                        canSort ? 'cursor-pointer transition-colors hover:text-text-primary' : ''
                      }`}
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <div className="flex items-center gap-1.5">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {canSort && (
                          <span className="text-text-muted">
                            {isSorted === 'asc' ? (
                              <ChevronUp className="w-3.5 h-3.5 text-apple-blue" />
                            ) : isSorted === 'desc' ? (
                              <ChevronDown className="w-3.5 h-3.5 text-apple-blue" />
                            ) : (
                              <ChevronsUpDown className="w-3 h-3 opacity-30" />
                            )}
                          </span>
                        )}
                      </div>
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-border-subtle font-mono text-xs">
            {table.getRowModel().rows.length === 0 ? (
              <tr>
                <td
                  colSpan={columns.length}
                  className="px-4 py-12 text-center text-text-muted font-sans text-xs"
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => {
                const rowId = idAccessor ? idAccessor(row.original) : undefined;
                const isSelected = selectedRowId && rowId === selectedRowId;

                return (
                  <tr
                    key={row.id}
                    onClick={() => onRowClick && onRowClick(row.original)}
                    className={`transition-colors duration-150 ${
                      onRowClick ? 'cursor-pointer' : ''
                    } ${
                      isSelected
                        ? 'bg-surface-2 font-semibold text-text-primary'
                        : 'text-text-secondary hover:bg-surface-2 hover:text-text-primary'
                    }`}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="whitespace-nowrap px-4 py-2.5">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
