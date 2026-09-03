import * as React from "react";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  variant?: "info" | "error";
  children?: React.ReactNode;
}

const variantStyles: Record<NonNullable<ModalProps["variant"]>, string> = {
  info: "border-indigo-200",
  error: "border-red-200",
};

export function Modal({ open, onClose, title, variant = "info", children }: ModalProps) {
  React.useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <div
        className={cn(
          "max-h-[80vh] w-full max-w-2xl overflow-hidden rounded-lg border bg-white text-card-foreground shadow-lg",
          variantStyles[variant],
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b px-5 py-3">
          <h2 className="text-sm font-semibold text-gray-900">{title ?? (variant === "error" ? "Error" : "Details")}</h2>
          <button
            onClick={onClose}
            className="inline-flex items-center justify-center rounded-md p-1 text-gray-400 hover:bg-accent hover:text-gray-600"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="max-h-[calc(80vh-52px)] overflow-y-auto px-5 py-4">{children}</div>
      </div>
    </div>
  );
}