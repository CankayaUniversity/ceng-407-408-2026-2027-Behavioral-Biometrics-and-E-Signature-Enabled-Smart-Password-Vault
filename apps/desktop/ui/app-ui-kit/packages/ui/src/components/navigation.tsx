import type { ReactNode } from "react"
import { cn } from "cn"

export type NavigationItem = {
  id: string
  label: string
  icon?: ReactNode
  disabled?: boolean
}

export type NavigationProps = {
  items: readonly NavigationItem[]
  activeId: string
  onNavigate: (id: string) => void
  ariaLabel?: string
  className?: string
}

/** Presentation-only navigation; authorization remains in the application/services. */
export function Navigation({
  items,
  activeId,
  onNavigate,
  ariaLabel = "Main navigation",
  className,
}: NavigationProps) {
  return (
    <nav aria-label={ariaLabel} className={cn("flex w-60 flex-col gap-1 rounded-lg border bg-card p-2", className)}>
      {items.map(({ id, label, icon, disabled }) => (
        <button
          key={id}
          type="button"
          disabled={disabled}
          aria-current={id === activeId ? "page" : undefined}
          onClick={() => onNavigate(id)}
          className={cn(
            "flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm transition-colors",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
            "disabled:pointer-events-none disabled:opacity-50",
            id === activeId
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-muted hover:text-foreground",
          )}
        >
          {icon}
          <span>{label}</span>
        </button>
      ))}
    </nav>
  )
}
