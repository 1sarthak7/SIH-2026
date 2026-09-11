"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export function WebGLFallback({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "h-full w-full bg-gradient-to-br from-[#050507] via-[#14151d] to-[#0a0b12]",
        className
      )}
    >
      <div
        className="h-full w-full opacity-30"
        style={{
          backgroundImage:
            "radial-gradient(circle at 72% 34%, rgba(255,255,255,0.08), transparent 24%), radial-gradient(circle at 18% 74%, rgba(110,214,201,0.06), transparent 30%)",
        }}
      />
    </div>
  );
}

interface WebGLErrorBoundaryProps {
  children: React.ReactNode;
  fallback: React.ReactNode;
}

interface WebGLErrorBoundaryState {
  hasError: boolean;
}

export class WebGLErrorBoundary extends React.Component<
  WebGLErrorBoundaryProps,
  WebGLErrorBoundaryState
> {
  constructor(props: WebGLErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(): WebGLErrorBoundaryState {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback;
    }
    return this.props.children;
  }
}
