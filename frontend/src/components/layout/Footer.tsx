import type { ReactNode } from 'react'
import logoImage from '../../../images/logo.png'

interface FooterProps {
  onNavigate: (path: string, hash?: string) => void
}

interface FooterNavItem {
  label: string
  path: string
  hash?: string
}

const quickLinks: FooterNavItem[] = [
  { label: 'Overview', path: '/', hash: '#system-overview-section' },
  { label: 'Market', path: '/market' },
  { label: 'Execution', path: '/execution' },
  { label: 'System', path: '/system' },
] 

const resources: FooterNavItem[] = [
  { label: 'Model', path: '/model' },
  { label: 'Signals', path: '/market' },
  { label: 'Demo Rules', path: '/execution' },
  { label: 'Privacy', path: '/system' },
]

const footerTags = ['BTCUSDT 15m', 'Bybit Demo Only', 'Local-First'] as const

function FooterLink({
  label,
  path,
  hash,
  onNavigate,
}: {
  label: string
  path: string
  hash?: string
  onNavigate: (path: string, hash?: string) => void
}) {
  return (
    <button
      type="button"
      onClick={() => onNavigate(path, hash)}
      className="group inline-flex items-center gap-3 bg-transparent text-left text-[var(--text-secondary)] transition-colors duration-200 hover:text-[var(--text-primary)]"
    >
      <span className="text-[0.95rem] text-[rgba(167,159,225,0.86)] transition-transform duration-200 group-hover:translate-x-0.5">
        ›
      </span>
      <span className="font-['Manrope'] text-[0.98rem] font-medium">{label}</span>
    </button>
  )
}

function SocialIcon({ label, children }: { label: string; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-[rgba(165,176,230,0.14)] bg-[rgba(16,22,46,0.42)] text-[var(--text-secondary)] transition-colors duration-200 hover:text-[var(--text-primary)]"
    >
      {children}
    </button>
  )
}

export function Footer({ onNavigate }: FooterProps) {
  return (
    <footer className="w-full bg-[#141b33] pb-0 pt-10 sm:pt-12 lg:pt-14">
      <div className="mx-auto w-full max-w-[1380px]">
        <div className="grid gap-10 px-6 py-8 sm:px-8 sm:py-10 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.75fr)_minmax(0,0.75fr)] lg:gap-12 lg:px-10 lg:py-12">
          <div className="max-w-[24rem]">
            <div className="flex items-center gap-4">
              <img src={logoImage} alt="Trading Garden logo" className="h-16 w-auto object-contain" />
              <div>
                <p className="font-['Space_Grotesk'] text-[1.9rem] font-semibold tracking-[-0.03em] text-[var(--text-primary)]">
                  Trading Garden
                </p>
              </div>
            </div>
            <p className="mt-5 font-['Manrope'] text-[1.02rem] leading-8 text-[var(--text-secondary)]">
              A local-first crypto trading system for BTCUSDT 15m signal intelligence and guarded demo
              execution.
            </p>
          </div>

          <div>
            <p className="font-['Sora'] text-[0.88rem] font-semibold uppercase tracking-[0.16em] text-[rgba(181,174,229,0.88)]">
              Quick Links
            </p>
            <div className="mt-5 flex flex-col gap-4">
              {quickLinks.map((item) => (
                <FooterLink key={`${item.path}${item.hash ?? ''}`} {...item} onNavigate={onNavigate} />
              ))}
            </div>
          </div>

          <div>
            <p className="font-['Sora'] text-[0.88rem] font-semibold uppercase tracking-[0.16em] text-[rgba(181,174,229,0.88)]">
              Resources
            </p>
            <div className="mt-5 flex flex-col gap-4">
              {resources.map((item) => (
                <FooterLink key={`${item.path}${item.hash ?? ''}`} {...item} onNavigate={onNavigate} />
              ))}
            </div>
          </div>
        </div>

        <div className="h-px w-full bg-[rgba(159,171,225,0.12)]" />

        <div className="flex flex-wrap items-center justify-between gap-5 px-6 py-5 sm:px-8 lg:px-10">
          <p className="font-['Manrope'] text-[0.98rem] text-[var(--text-secondary)]">© 2026 Trading Garden</p>

          <div className="flex flex-wrap items-center justify-center gap-3">
            {footerTags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-2 rounded-full border border-[rgba(159,171,225,0.16)] bg-[rgba(18,24,46,0.54)] px-4 py-2 text-[0.94rem] text-[var(--text-secondary)]"
              >
                <span className="h-2 w-2 rounded-full bg-[rgba(157,144,255,0.92)]" />
                <span>{tag}</span>
              </span>
            ))}
          </div>

          <div className="flex items-center gap-3">
            <SocialIcon label="GitHub">
              <svg viewBox="0 0 24 24" fill="currentColor" className="h-[18px] w-[18px]" aria-hidden="true">
                <path d="M12 2C6.48 2 2 6.58 2 12.22c0 4.5 2.87 8.32 6.84 9.66.5.1.68-.22.68-.5 0-.24-.01-1.04-.01-1.88-2.78.62-3.37-1.2-3.37-1.2-.46-1.18-1.11-1.5-1.11-1.5-.91-.64.07-.62.07-.62 1 .08 1.53 1.06 1.53 1.06.9 1.56 2.35 1.11 2.92.85.09-.67.35-1.11.64-1.36-2.22-.26-4.56-1.14-4.56-5.06 0-1.12.39-2.03 1.03-2.75-.1-.26-.45-1.3.1-2.7 0 0 .84-.28 2.75 1.05A9.3 9.3 0 0 1 12 6.82c.85 0 1.71.12 2.52.35 1.91-1.33 2.75-1.05 2.75-1.05.55 1.4.2 2.44.1 2.7.64.72 1.03 1.63 1.03 2.75 0 3.93-2.35 4.8-4.58 5.05.36.32.68.94.68 1.9 0 1.38-.01 2.49-.01 2.83 0 .28.18.61.69.5A10.25 10.25 0 0 0 22 12.22C22 6.58 17.52 2 12 2Z" />
              </svg>
            </SocialIcon>
            <SocialIcon label="Twitter X">
              <svg viewBox="0 0 24 24" fill="currentColor" className="h-[18px] w-[18px]" aria-hidden="true">
                <path d="M18.9 2H21l-6.55 7.49L22 22h-5.94l-4.65-6.09L6.07 22H4l7.01-8.01L2 2h6.09l4.2 5.55L18.9 2Zm-1.04 18h1.64L7.2 3.9H5.44L17.86 20Z" />
              </svg>
            </SocialIcon>
            <SocialIcon label="Telegram">
              <svg viewBox="0 0 24 24" fill="currentColor" className="h-[18px] w-[18px]" aria-hidden="true">
                <path d="M21.44 4.62c.3-.12.62.15.54.47l-2.91 13.73c-.06.29-.38.44-.63.3l-4.3-2.46-2.2 2.13c-.2.19-.53.08-.57-.2l-.44-3.6 7.62-6.89c.22-.2-.02-.55-.28-.4l-9.42 5.95-4.07-1.38c-.32-.11-.35-.55-.05-.7l16.71-7.95Z" />
              </svg>
            </SocialIcon>
          </div>
        </div>
      </div>
    </footer>
  )
}
