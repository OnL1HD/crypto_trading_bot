import { useEffect, useState, type CSSProperties } from 'react'
import heroSectionImage from '../../images/hero_section.png'
import heroAnimationFrame1 from '../../images/hero_animation/1.png'
import heroAnimationFrame2 from '../../images/hero_animation/2.png'
import heroAnimationFrame3 from '../../images/hero_animation/3.png'
import heroAnimationFrame4 from '../../images/hero_animation/4.png'
import heroAnimationFrame5 from '../../images/hero_animation/5.png'
import heroAnimationFrame6 from '../../images/hero_animation/6.png'
import heroAnimationFrame7 from '../../images/hero_animation/7.png'
import heroAnimationFrame8 from '../../images/hero_animation/8.png'
import heroAnimationFrame9 from '../../images/hero_animation/9.png'
import heroAnimationFrame10 from '../../images/hero_animation/10.png'
import DecryptedText from '../components/hero/DecryptedText'
import { SystemOverviewSection } from '../components/sections/SystemOverviewSection'

const HERO_SECTION_HEIGHT = '100dvh'
const HERO_ANIMATION_FRAMES = [
  heroAnimationFrame1,
  heroAnimationFrame2,
  heroAnimationFrame3,
  heroAnimationFrame4,
  heroAnimationFrame5,
  heroAnimationFrame6,
  heroAnimationFrame7,
  heroAnimationFrame8,
  heroAnimationFrame9,
  heroAnimationFrame10,
]
const HERO_ANIMATION_FPS = 3

interface HomePageProps {
  onNavigate: (path: string, hash?: string) => void
}

export function HomePage({ onNavigate }: HomePageProps) {
  const [heroFrameIndex, setHeroFrameIndex] = useState(0)

  useEffect(() => {
    HERO_ANIMATION_FRAMES.forEach((src) => {
      const image = new Image()
      image.src = src
    })

    const frameDuration = Math.max(80, Math.floor(1000 / HERO_ANIMATION_FPS))
    const intervalId = window.setInterval(() => {
      setHeroFrameIndex((current) => (current + 1) % HERO_ANIMATION_FRAMES.length)
    }, frameDuration)

    return () => {
      window.clearInterval(intervalId)
    }
  }, [])

  return (
    <>
      <section
        id="hero-section"
        className="dashboard-hero"
        aria-label="Hero background section"
        style={{ '--hero-height': HERO_SECTION_HEIGHT } as CSSProperties}
      >
        <div className="dashboard-hero__bg" aria-hidden="true">
          <div className="dashboard-hero__bg-base" />
          <div className="dashboard-hero__bg-glow dashboard-hero__bg-glow--violet" />
          <div className="dashboard-hero__bg-glow dashboard-hero__bg-glow--blue" />
          <div className="dashboard-hero__bg-rings" />
          <div className="dashboard-hero__bg-particles" />
          <div className="dashboard-hero__bg-vignette" />
        </div>
        <div className="dashboard-hero__content">
          <div className="dashboard-hero__image-frame">
            <img
              className="dashboard-hero__image"
              src={HERO_ANIMATION_FRAMES[heroFrameIndex] ?? heroSectionImage}
              alt="Trading Garden animated hero"
            />
          </div>
          <div className="dashboard-hero__copy">
            <div className="dashboard-hero__kicker">
              <span className="dashboard-hero__kicker-line" />
              <span className="dashboard-hero__kicker-star" aria-hidden="true" />
              <span>Autonomous trading bot</span>
              <span className="dashboard-hero__kicker-line" />
            </div>
            <DecryptedText
              text="Trading Garden"
              speed={150}
              maxIterations={10}
              sequential
              animateOn="inViewHover"
              className="text-[var(--text-primary)]"
              encryptedClassName="text-[var(--text-secondary)]"
              parentClassName="hero-brand-text dashboard-hero__title text-[clamp(1.05rem,3.3vw,2.6rem)] font-semibold tracking-[0.1em]"
            />
            <p className="dashboard-hero__description">
              A cinematic control surface for live market structure, model conviction, and guarded demo
              execution in one calm view.
            </p>
            <div className="dashboard-hero__pill-row" aria-label="Hero highlights">
              <div className="hero-pill">
                <span className="hero-pill__icon" aria-hidden="true">
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M1.5 8h2l1.1-2.2L6.7 11l1.9-6 1.6 3H14.5" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <span>Live signals</span>
              </div>
              <div className="hero-pill">
                <span className="hero-pill__icon" aria-hidden="true">
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M8 1.8 12.7 3.8v3.5c0 3-2 5.8-4.7 6.9C5.3 13.1 3.3 10.3 3.3 7.3V3.8L8 1.8Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
                    <path d="m6.3 8 1.2 1.2 2.2-2.5" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
                <span>Guarded execution</span>
              </div>
              <div className="hero-pill">
                <span className="hero-pill__icon" aria-hidden="true">
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M5 2.3v11.4M11 2.3v11.4M2.3 5h11.4M2.3 11h11.4" stroke="currentColor" strokeWidth="1.15" strokeLinecap="round" />
                    <circle cx="5" cy="5" r="1.1" fill="currentColor" />
                    <circle cx="11" cy="8" r="1.1" fill="currentColor" />
                    <circle cx="5" cy="11" r="1.1" fill="currentColor" />
                  </svg>
                </span>
                <span>Autonomous strategies</span>
              </div>
            </div>
            <div className="dashboard-hero__actions">
              <button type="button" className="hero-glow-button" onClick={() => onNavigate('/market')}>
                <span>Explore the chart</span>
                <span className="hero-button__icon" aria-hidden="true">
                  <svg viewBox="0 0 16 16" fill="none">
                    <path d="M3 8h9" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" />
                    <path d="m8.8 3.8 4.2 4.2-4.2 4.2" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </span>
              </button>
            </div>
          </div>
        </div>
      </section>

      <SystemOverviewSection />
    </>
  )
}
