import overviewBackgroundImage from '../../../images/Overview_bg.png'

const supportItems = [
  {
    title: 'Local-First',
    description: 'All data, inference, and logs stored locally with parquet files.',
    icon: (
      <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <ellipse cx="10" cy="4.5" rx="4.75" ry="2.25" stroke="currentColor" strokeWidth="1.4" />
        <path d="M5.25 4.5v4.1c0 1.24 2.13 2.25 4.75 2.25s4.75-1.01 4.75-2.25V4.5" stroke="currentColor" strokeWidth="1.4" />
        <path d="M5.25 8.7v4.1c0 1.24 2.13 2.25 4.75 2.25s4.75-1.01 4.75-2.25V8.7" stroke="currentColor" strokeWidth="1.4" />
      </svg>
    ),
  },
  {
    title: 'Guard Rails',
    description: 'Multiple safety checks protect every execution attempt.',
    icon: (
      <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <path d="M10 2.5 15 4.6v3.8c0 3.2-2.13 6.07-5 7.22-2.87-1.15-5-4.02-5-7.22V4.6L10 2.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
        <path d="m7.85 9.8 1.45 1.45 2.85-3.3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    title: 'Demo Execution',
    description: 'Bybit demo trading with manual, controlled execution.',
    icon: (
      <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
        <rect x="3.6" y="4.2" width="12.8" height="9" rx="2" stroke="currentColor" strokeWidth="1.4" />
        <path d="M8.2 15.8h3.6M10 13.2v2.6M8 8.1l1.8 1.6L12.4 7" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
] as const

const pipelineItems = [
  {
    step: '01',
    title: 'Market Data',
    description: 'BTCUSDT 15m data ingestion and continuous refresh.',
    emphasized: false,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <ellipse cx="12" cy="6" rx="5.2" ry="2.7" stroke="currentColor" strokeWidth="1.5" />
        <path d="M6.8 6v4.7c0 1.5 2.33 2.7 5.2 2.7s5.2-1.2 5.2-2.7V6" stroke="currentColor" strokeWidth="1.5" />
        <path d="M6.8 10.8v4.7c0 1.5 2.33 2.7 5.2 2.7s5.2-1.2 5.2-2.7v-4.7" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    ),
  },
  {
    step: '02',
    title: 'Feature Engine',
    description: 'Engineered features and labels shape market context for the model.',
    emphasized: false,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M5.5 17.5V12M10.5 17.5V8M15.5 17.5V5.5M20.5 17.5V10" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    step: '03',
    title: 'Model Inference',
    description: 'The model evaluates structure and direction to produce high-quality signals.',
    emphasized: false,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M9.2 5.2c-1.8 0-3.3 1.46-3.3 3.27 0 .72.23 1.38.63 1.92-1.43.62-2.43 2.05-2.43 3.72 0 2.24 1.8 4.06 4.02 4.06H9.8M14.8 5.2c1.8 0 3.3 1.46 3.3 3.27 0 .72-.23 1.38-.63 1.92 1.43.62 2.43 2.05 2.43 3.72 0 2.24-1.8 4.06-4.02 4.06H14.2" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M12 4.8v14.4M9.2 8.8h5.6M9.2 15.2h5.6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    step: '04',
    title: 'Signal Layer',
    description: 'Signals are stored locally with full history and surfaced in the dashboard.',
    emphasized: false,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M3.8 12.2h4.1l1.85-4.1 3.05 8.1 2.45-5h4.95" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    step: '05',
    title: 'Guarded Execution',
    description: 'Latest stored signal runs through strict guards before demo execution on Bybit.',
    emphasized: true,
    icon: (
      <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M12 4.2 17.2 6.4v4.2c0 3.35-2.17 6.37-5.2 7.58-3.03-1.21-5.2-4.23-5.2-7.58V6.4L12 4.2Z" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
        <path d="M12 8.2v4.5M9.75 10.45h4.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    ),
  },
] as const

export function SystemOverviewSection() {
  return (
    <section
      id="system-overview-section"
      aria-labelledby="system-overview-title"
      className="relative scroll-mt-28 overflow-hidden px-2 py-8 sm:px-3 sm:py-10 lg:px-4"
    >
      <div className="pointer-events-none absolute inset-0 opacity-80">
        <img
          src={overviewBackgroundImage}
          alt=""
          aria-hidden="true"
          className="absolute left-1/2 top-0 h-full w-[108%] max-w-none -translate-x-1/2 object-cover"
        />
        <div className="absolute inset-x-0 top-0 h-full bg-[radial-gradient(circle_at_50%_0%,rgba(145,132,255,0.1),transparent_42%)]" />
        <div className="absolute left-1/2 top-14 h-[32rem] w-[70rem] -translate-x-1/2 rounded-full bg-[radial-gradient(circle,rgba(116,114,255,0.08)_0%,rgba(116,114,255,0.03)_45%,transparent_72%)] blur-3xl" />
      </div>

      <div className="mx-auto w-[min(99vw,1720px)]">
        <div className="relative overflow-hidden rounded-[32px] border border-[rgba(150,168,255,0.16)] bg-transparent px-5 py-8 shadow-[0_24px_70px_rgba(3,7,24,0.32),inset_0_1px_0_rgba(255,255,255,0.04)] sm:px-7 sm:py-10 lg:px-9 lg:py-10 xl:px-10">
          <div className="pointer-events-none absolute inset-0">
            <div className="absolute inset-[1px] rounded-[31px] border border-[rgba(196,177,255,0.05)]" />
            <div className="absolute -left-16 bottom-0 h-32 w-32 rounded-tr-[3rem] border-l border-t border-[rgba(114,136,255,0.08)] opacity-60" />
            <div className="absolute left-[55%] top-8 h-[28rem] w-[50rem] -translate-x-1/2 rounded-full border border-[rgba(180,148,255,0.09)]" />
            <div className="absolute left-[58%] top-10 h-[18rem] w-[42rem] -translate-x-1/2 rounded-full border border-[rgba(180,148,255,0.05)]" />
            <div className="absolute right-14 top-28 h-28 w-28 rounded-full bg-[radial-gradient(circle,rgba(177,126,255,0.18)_0%,rgba(177,126,255,0.05)_42%,transparent_74%)] blur-2xl" />
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_20%,rgba(255,255,255,0.16)_0_1px,transparent_1.5px),radial-gradient(circle_at_32%_52%,rgba(255,255,255,0.12)_0_1px,transparent_1.5px),radial-gradient(circle_at_67%_11%,rgba(255,255,255,0.14)_0_1px,transparent_1.5px),radial-gradient(circle_at_76%_76%,rgba(255,255,255,0.1)_0_1px,transparent_1.5px),radial-gradient(circle_at_90%_21%,rgba(255,255,255,0.12)_0_1px,transparent_1.5px)] opacity-60" />
          </div>

          <div className="relative z-[1] grid gap-8 lg:grid-cols-[minmax(15.5rem,0.6fr)_minmax(0,2.9fr)] lg:items-start lg:gap-6 xl:gap-8">
            <div className="max-w-[21rem] pt-1 xl:max-w-[22rem]">
              <p className="mb-4 font-['Sora'] text-[0.7rem] font-semibold uppercase tracking-[0.32em] text-[var(--text-muted)] sm:mb-4">
                System overview
              </p>
              <h2
                id="system-overview-title"
                className="max-w-[12ch] font-['Space_Grotesk'] text-[clamp(1.95rem,2vw,3.05rem)] font-semibold leading-[1.08] text-[var(--text-primary)]"
              >
                From market structure
                <br />
                to guarded <span className="bg-[linear-gradient(135deg,#E3D5FF_0%,#C790FF_42%,#8D73FF_100%)] bg-clip-text text-transparent">execution</span>
              </h2>
              <p className="mt-4 max-w-[22rem] font-['Manrope'] text-[0.9rem] leading-8 text-[var(--text-secondary)]">
                Trading Garden is a complete decision pipeline designed to bring clarity, control,
                and discipline to the trading process.
              </p>

              <div className="mt-7 space-y-4 sm:mt-8">
                {supportItems.map((item) => (
                  <div key={item.title} className="flex items-start gap-3.5">
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-[rgba(160,173,255,0.16)] bg-[linear-gradient(180deg,rgba(19,28,66,0.88),rgba(11,18,44,0.72))] text-[#BE96FF] shadow-[0_0_20px_rgba(117,104,255,0.12),inset_0_1px_0_rgba(255,255,255,0.04)]">
                      <div className="h-7 w-7">{item.icon}</div>
                    </div>
                    <div className="space-y-1">
                      <h3 className="font-['Manrope'] text-[1rem] font-semibold text-[rgb(108,48,177)]">
                        {item.title}
                      </h3>
                      <p className="max-w-[18rem] font-['Manrope'] text-[0.85rem] leading-7 text-[var(--text-primary)]">
                        {item.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative pt-1">
              <div className="absolute left-1/2 top-[0.5rem] hidden h-24 w-[43.3rem] -translate-x-1/2 lg:block xl:w-[58rem]">
                <div className="system-overview-signal" aria-hidden="true" />
                <div className="absolute inset-x-0 top-[0.72rem] h-[1.65rem] border border-b-0 border-dashed border-[rgba(189,151,255,0.6)] rounded-t-[1.15rem]" />
                <div className="absolute inset-x-[5%] top-8 h-20 rounded-[50%] border-t border-[rgba(168,136,255,0.18)]" />
                {pipelineItems.slice(1, 4).map((item, index) => (
                  <div
                    key={`${item.step}-cutout`}
                    className="absolute top-[0.64rem] z-[1] h-[3px] w-[1.9rem] -translate-x-1/2 bg-[#1a1d4b]"
                    style={{ left: `${(index + 1) * 25}%` }}
                  />
                ))}
                {pipelineItems.slice(1, 4).map((item, index) => (
                  <div
                    key={`${item.step}-curve`}
                    className="absolute top-[0.72rem] z-[2] h-[1.35rem] w-[1.6rem] -translate-x-1/2 rounded-b-[1rem] border-x border-b border-dashed border-[rgba(189,151,255,0.6)]"
                    style={{ left: `${(index + 1) * 25}%` }}
                  />
                ))}
                {pipelineItems.map((item, index) => (
                  <div
                    key={item.step}
                    className="absolute top-[1.78rem] h-2.5 w-2.5 -translate-x-1/2 rounded-full bg-[#d7bcff] shadow-[0_0_12px_rgba(197,153,255,0.9)]"
                    style={{ left: `${index * 25}%` }}
                  />
                ))}
                <div className="absolute right-0 top-[1.1rem] h-14 w-14 rounded-full bg-[radial-gradient(circle,rgba(213,161,255,0.72)_0%,rgba(180,124,255,0.24)_40%,transparent_72%)] blur-xl" />
              </div>

              <div className="relative overflow-x-auto pb-2 lg:overflow-visible">
                <div className="flex min-w-[58rem] gap-2.5 pr-1 pt-12 lg:min-w-0 lg:justify-center lg:pt-14 xl:gap-10">
                  {pipelineItems.map((item) => (
                    <article
                      key={item.step}
                      className={[
                        'relative flex min-h-[16.5rem] w-[10.2rem] shrink-0 flex-col rounded-[22px] border px-8 pb-12 pt-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] xl:w-[12rem]',
                        item.emphasized
                          ? 'system-overview-terminal-card border-[rgba(214,168,255,0.58)] bg-[linear-gradient(180deg,rgba(33,27,70,0.95),rgba(18,16,47,0.88))] shadow-[0_0_0_1px_rgba(244,241,255,0.06),0_0_22px_rgba(176,117,255,0.28),0_16px_36px_rgba(17,17,44,0.36)]'
                          : 'border-[rgba(143,161,237,0.16)] bg-[linear-gradient(180deg,rgba(16,24,58,0.92),rgba(11,18,44,0.74))] shadow-[0_12px_28px_rgba(8,11,32,0.22)]',
                      ].join(' ')}
                    >
                      <div className={[
                        'mb-6 inline-flex h-9 w-9 items-center justify-center rounded-xl border text-[0.92rem] font-semibold',
                        item.emphasized
                          ? 'border-[rgba(216,174,255,0.36)] bg-[rgba(126,88,255,0.16)] text-[#D6BCFF]'
                          : 'border-[rgba(159,172,236,0.14)] bg-[rgba(90,103,188,0.14)] text-[#9A94EF]',
                      ].join(' ')}>
                        {item.step}
                      </div>
                      <div className={[
                        'mb-5 h-10 w-10',
                        item.emphasized ? 'text-[#D9B7FF]' : 'text-[#B48BFF]',
                      ].join(' ')}>
                        {item.icon}
                      </div>
                      <h3 className="font-['Manrope'] text-[0.99rem] font-semibold text-[var(--text-primary)]">
                        {item.title}
                      </h3>
                      <p className="mt-3 font-['Manrope'] text-[0.94rem] leading-8 text-[var(--text-secondary)]">
                        {item.description}
                      </p>
                    </article>
                  ))}
                </div>
              </div>

              <div className="mt-6 px-1 lg:mt-7 lg:px-6 xl:px-7">
                <div className="flex w-full items-center gap-3 rounded-full border border-[rgba(168,181,255,0.18)] bg-[linear-gradient(180deg,rgba(16,23,57,0.8),rgba(10,16,39,0.76))] px-5 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04),0_0_26px_rgba(108,102,255,0.09)] sm:px-7 sm:py-5">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[rgba(180,162,255,0.22)] bg-[rgba(74,67,141,0.16)] text-[#CBA9FF]">
                    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true" className="h-5 w-5">
                      <path d="M10 2.5 15 4.6v3.8c0 3.2-2.13 6.07-5 7.22-2.87-1.15-5-4.02-5-7.22V4.6L10 2.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
                      <path d="m7.85 9.8 1.45 1.45 2.85-3.3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </div>
                  <p className="font-['Manrope'] text-[0.98rem] leading-7 text-[var(--text-primary)] sm:text-[1rem]">
                    Protected by freshness checks, cooldowns, position limits, and duplicate prevention.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
