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
}

export function DataTable<TData>({
  columns,
  data,
  onRowClick,
  selectedRowId,
  idAccessor,
  emptyMessage = 'No records in ledger.',
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
    <div className="w-full overflow-hidden panel rounded-2xl border border-border-subtle shadow-soft">
      <div className="overflow-x-auto max-h-[560px]">
        <table className="w-full text-left text-xs border-collapse">
          <thead className="bg-surface-2/60 backdrop-blur-md sticky top-0 z-10 border-b border-border-subtle text-text-secondary uppercase tracking-wider font-sans font-semibold text-[11px]">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  const isSorted = header.column.getIsSorted();

                  return (
                    <th
                      key={header.id}
                      className={`px-4 py-3 select-none ${
                        canSort ? 'cursor-pointer hover:text-text-primary transition-colors' : ''
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
          <tbody className="divide-y divide-border-subtle/30 font-mono text-xs">
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
                    className={`transition-all duration-150 ${
                      onRowClick ? 'cursor-pointer' : ''
                    } ${
                      isSelected
                        ? 'bg-surface-hover/90 text-text-primary font-semibold shadow-inner'
                        : 'hover:bg-surface-hover/50 text-text-secondary hover:text-text-primary'
                    }`}
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-2.5 whitespace-nowrap">
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
