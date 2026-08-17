import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  widthClass?: string;
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  widthClass = 'max-w-xl',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden animate-fade-in">
      {/* Apple Frosted Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      <div className="fixed inset-y-0 right-0 flex max-w-full pl-6 sm:pl-10">
        <div
          className={`w-screen ${widthClass} bg-surface-1/90 backdrop-blur-2xl border-l border-border-highlight rounded-l-3xl flex flex-col justify-between shadow-float transform transition-transform duration-300 ease-out`}
        >
          {/* Sheet Header */}
          <div className="px-6 py-4 border-b border-border-subtle flex items-center justify-between bg-surface-2/60 backdrop-blur-md rounded-tl-3xl">
            <div>
              <h2 className="text-sm font-semibold text-text-primary tracking-tight font-sans">
                {title}
              </h2>
              {subtitle && (
                <p className="text-xs font-mono text-text-muted mt-0.5">{subtitle}</p>
              )}
            </div>
            <button
              onClick={onClose}
              className="rounded-full p-1.5 text-text-muted hover:text-text-primary hover:bg-surface-hover bg-surface-2 border border-border-subtle transition-all hover:scale-105 active:scale-95 cursor-pointer"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Content body */}
          <div className="flex-1 overflow-y-auto p-6 space-y-5">{children}</div>
        </div>
      </div>
    </div>
  );
};
