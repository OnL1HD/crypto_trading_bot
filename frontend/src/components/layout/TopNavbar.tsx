import logoImage from '../../../images/logo.png'

interface TopNavbarProps {
  currentPath: string
  onNavigate: (path: string, hash?: string) => void
}

interface NavItem {
  label: string
  path: string
  hash?: string
}

const navItems: NavItem[] = [
  { label: 'Home', path: '/' },
  { label: 'Market', path: '/market' },
  { label: 'Model', path: '/model' },
  { label: 'Execution', path: '/execution' },
  { label: 'System', path: '/system' },
]

export function TopNavbar({ currentPath, onNavigate }: TopNavbarProps) {
  return (
    <header className="fixed inset-x-0 top-0 z-50 px-4 pt-3 max-[840px]:px-3 max-[840px]:pt-2.5">
      <div className="mx-auto flex w-full max-w-[1180px] items-center gap-4 rounded-full border border-[rgba(255,255,255,0.18)] bg-[rgba(6,10,24,0.84)] px-4 py-2 shadow-[0_18px_45px_rgba(0,0,0,0.28)] animate-[fade-in-up_520ms_ease-out] max-[840px]:gap-3 max-[840px]:px-3.5 max-[840px]:py-1.5">
        <div className="flex min-w-0 items-center gap-3">
          <img
            src={logoImage}
            alt="Trading Garden logo"
            className="-ml-10 h-11 w-auto shrink-0 origin-left scale-200 object-contain max-[840px]:-ml-1 max-[840px]:h-10"
          />
          <nav className="ml-8 flex items-center gap-5 max-[840px]:ml-5 max-[840px]:gap-3.5" aria-label="Primary sections">
            {navItems.map((item) => {
              const isActive = item.hash ? false : currentPath === item.path

              return (
                <button
                  key={`${item.path}${item.hash ?? ''}`}
                  type="button"
                  onClick={() => onNavigate(item.path, item.hash)}
                  className={[
                    'inline-flex cursor-pointer items-center justify-center bg-transparent px-1 py-1 font-[\'Sora\'] text-sm font-semibold tracking-[0.04em] transition-opacity duration-200 hover:opacity-75',
                    isActive ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]',
                  ].join(' ')}
                >
                  {item.label}
                </button>
              )
            })}
          </nav>
        </div>
      </div>
    </header>
  )
}
