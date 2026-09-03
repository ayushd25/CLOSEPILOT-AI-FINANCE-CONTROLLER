"use client";

import * as React from "react";
import { Modal } from "@/components/ui/modal";

export const GLOBAL_API_ERROR_EVENT = "closepilot:api-error";

export interface GlobalApiErrorDetail {
  method: string;
  path: string;
  message: string;
}

interface DisplayedError {
  detail: GlobalApiErrorDetail;
}

/**
 * Surfaces otherwise-silent API/network failures (e.g. backend unreachable)
 * as a closable global modal on any page. Embraces an event-based contract so
 * the plain `HttpClient` (used across pages) can report without coupling to
 * React context.
 */
export function GlobalErrorProvider({ children }: { children: React.ReactNode }) {
  const [error, setError] = React.useState<DisplayedError | null>(null);

  React.useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<GlobalApiErrorDetail>).detail;
      if (detail) setError({ detail });
    };
    window.addEventListener(GLOBAL_API_ERROR_EVENT, handler);
    return () => window.removeEventListener(GLOBAL_API_ERROR_EVENT, handler);
  }, []);

  const isUnreachable = error?.detail.message?.toLowerCase().includes("fetch") ?? false;

  return (
    <>
      {children}
      <Modal
        open={error !== null}
        onClose={() => setError(null)}
        variant="error"
        title={isUnreachable ? "Backend unreachable" : "API request failed"}
      >
        <dl className="space-y-3">
          {error && (
            <>
              <div>
                <dt className="text-xs font-semibold text-gray-500">Message</dt>
                <dd className="mt-0.5 font-mono text-xs break-words whitespace-pre-wrap">
                  {error.detail.message}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-semibold text-gray-500">Endpoint</dt>
                <dd className="mt-0.5 font-mono text-xs">
                  {error.detail.method} {error.detail.path}
                </dd>
              </div>
              {isUnreachable && (
                <div>
                  <dt className="text-xs font-semibold text-gray-500">How to fix</dt>
                  <dd className="mt-0.5 text-xs">
                    The API backend is not reachable. Start the stack with{" "}
                    <span className="font-mono">docker compose up -d</span> and try again.
                  </dd>
                </div>
              )}
            </>
          )}
        </dl>
      </Modal>
    </>
  );
}