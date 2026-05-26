import type { PropsWithChildren } from 'react'

interface AppShellProps extends PropsWithChildren {
  className?: string
}

export function AppShell({ children, className }: AppShellProps) {
  return (
    <div
      className={className ? `app-shell ${className}` : 'app-shell'}
    >
      <main className="flex flex-col gap-5">{children}</main>
    </div>
  )
}
