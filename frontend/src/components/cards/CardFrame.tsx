import type { PropsWithChildren, ReactNode } from 'react'

interface CardFrameProps extends PropsWithChildren {
  title: string
  subtitle?: string
  className?: string
  statusSlot?: ReactNode
}

export function CardFrame({ title, subtitle, className, statusSlot, children }: CardFrameProps) {
  return (
    <section className={className ? `card-frame ${className}` : 'card-frame'}>
      <header className="card-frame__header">
        <div className="card-frame__header-copy">
          <h2>{title}</h2>
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
        {statusSlot ? <div className="card-frame__status">{statusSlot}</div> : null}
      </header>
      <div className="card-frame__body">{children}</div>
    </section>
  )
}
