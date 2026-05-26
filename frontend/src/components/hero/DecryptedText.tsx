import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ComponentProps } from 'react'
import { motion } from 'framer-motion'

type RevealDirection = 'start' | 'end' | 'center'
type AnimateOn = 'hover' | 'click' | 'view' | 'inViewHover'
type ClickMode = 'once' | 'toggle'

interface DecryptedTextProps extends Omit<ComponentProps<typeof motion.span>, 'children'> {
  text: string
  speed?: number
  maxIterations?: number
  sequential?: boolean
  revealDirection?: RevealDirection
  useOriginalCharsOnly?: boolean
  characters?: string
  className?: string
  parentClassName?: string
  encryptedClassName?: string
  animateOn?: AnimateOn
  clickMode?: ClickMode
}

export default function DecryptedText({
  text,
  speed = 50,
  maxIterations = 10,
  sequential = false,
  revealDirection = 'start',
  useOriginalCharsOnly = false,
  characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz!@#$%^&*()_+',
  className = '',
  parentClassName = '',
  encryptedClassName = '',
  animateOn = 'hover',
  clickMode = 'once',
  ...props
}: DecryptedTextProps) {
  const [displayText, setDisplayText] = useState(text)
  const [isAnimating, setIsAnimating] = useState(false)
  const [revealedIndices, setRevealedIndices] = useState<Set<number>>(new Set())
  const [hasAnimated, setHasAnimated] = useState(false)
  const [isDecrypted, setIsDecrypted] = useState(animateOn !== 'click')
  const [direction, setDirection] = useState<'forward' | 'reverse'>('forward')

  const containerRef = useRef<HTMLSpanElement | null>(null)
  const orderRef = useRef<number[]>([])
  const pointerRef = useRef(0)

  const availableChars = useMemo(() => {
    const chars = useOriginalCharsOnly
      ? Array.from(new Set(text.split(''))).filter((char) => char !== ' ')
      : characters.split('')

    if (chars.length > 0) {
      return chars
    }

    return characters.split('')
  }, [useOriginalCharsOnly, text, characters])

  const shuffleText = useCallback(
    (originalText: string, currentRevealed: Set<number>) => {
      return originalText
        .split('')
        .map((char, i) => {
          if (char === ' ') {
            return ' '
          }
          if (currentRevealed.has(i)) {
            return originalText[i]
          }
          return availableChars[Math.floor(Math.random() * availableChars.length)]
        })
        .join('')
    },
    [availableChars],
  )

  const computeOrder = useCallback(
    (length: number) => {
      const order: number[] = []
      if (length <= 0) {
        return order
      }

      if (revealDirection === 'start') {
        for (let i = 0; i < length; i += 1) {
          order.push(i)
        }
        return order
      }

      if (revealDirection === 'end') {
        for (let i = length - 1; i >= 0; i -= 1) {
          order.push(i)
        }
        return order
      }

      const middle = Math.floor(length / 2)
      let offset = 0

      while (order.length < length) {
        if (offset % 2 === 0) {
          const idx = middle + offset / 2
          if (idx >= 0 && idx < length) {
            order.push(idx)
          }
        } else {
          const idx = middle - Math.ceil(offset / 2)
          if (idx >= 0 && idx < length) {
            order.push(idx)
          }
        }
        offset += 1
      }

      return order.slice(0, length)
    },
    [revealDirection],
  )

  const fillAllIndices = useCallback(() => {
    const indices = new Set<number>()
    for (let i = 0; i < text.length; i += 1) {
      indices.add(i)
    }
    return indices
  }, [text])

  const removeRandomIndices = useCallback((set: Set<number>, count: number) => {
    const array = Array.from(set)
    for (let i = 0; i < count && array.length > 0; i += 1) {
      const idx = Math.floor(Math.random() * array.length)
      array.splice(idx, 1)
    }
    return new Set(array)
  }, [])

  const encryptInstantly = useCallback(() => {
    const empty = new Set<number>()
    setRevealedIndices(empty)
    setDisplayText(shuffleText(text, empty))
    setIsDecrypted(false)
  }, [text, shuffleText])

  const triggerDecrypt = useCallback(() => {
    if (sequential) {
      orderRef.current = computeOrder(text.length)
      pointerRef.current = 0
      setRevealedIndices(new Set())
    } else {
      setRevealedIndices(new Set())
    }

    setDirection('forward')
    setIsAnimating(true)
  }, [sequential, computeOrder, text.length])

  const triggerReverse = useCallback(() => {
    if (sequential) {
      orderRef.current = computeOrder(text.length).slice().reverse()
      pointerRef.current = 0
      const all = fillAllIndices()
      setRevealedIndices(all)
      setDisplayText(shuffleText(text, all))
    } else {
      const all = fillAllIndices()
      setRevealedIndices(all)
      setDisplayText(shuffleText(text, all))
    }

    setDirection('reverse')
    setIsAnimating(true)
  }, [sequential, computeOrder, fillAllIndices, shuffleText, text])

  useEffect(() => {
    if (!isAnimating) {
      return
    }

    let currentIteration = 0

    const getNextIndex = (revealedSet: Set<number>) => {
      const textLength = text.length

      switch (revealDirection) {
        case 'start':
          return revealedSet.size
        case 'end':
          return textLength - 1 - revealedSet.size
        case 'center': {
          const middle = Math.floor(textLength / 2)
          const offset = Math.floor(revealedSet.size / 2)
          const nextIndex = revealedSet.size % 2 === 0 ? middle + offset : middle - offset - 1

          if (nextIndex >= 0 && nextIndex < textLength && !revealedSet.has(nextIndex)) {
            return nextIndex
          }

          for (let i = 0; i < textLength; i += 1) {
            if (!revealedSet.has(i)) {
              return i
            }
          }
          return 0
        }
      }
    }

    const interval = setInterval(() => {
      setRevealedIndices((prevRevealed) => {
        if (sequential) {
          if (direction === 'forward') {
            if (prevRevealed.size < text.length) {
              const nextIndex = getNextIndex(prevRevealed)
              const newRevealed = new Set(prevRevealed)
              newRevealed.add(nextIndex)
              setDisplayText(shuffleText(text, newRevealed))
              return newRevealed
            }

            clearInterval(interval)
            setIsAnimating(false)
            setIsDecrypted(true)
            return prevRevealed
          }

          if (pointerRef.current < orderRef.current.length) {
            const idxToRemove = orderRef.current[pointerRef.current]
            pointerRef.current += 1
            const newRevealed = new Set(prevRevealed)
            newRevealed.delete(idxToRemove)
            setDisplayText(shuffleText(text, newRevealed))

            if (newRevealed.size === 0) {
              clearInterval(interval)
              setIsAnimating(false)
              setIsDecrypted(false)
            }

            return newRevealed
          }

          clearInterval(interval)
          setIsAnimating(false)
          setIsDecrypted(false)
          return prevRevealed
        }

        if (direction === 'forward') {
          setDisplayText(shuffleText(text, prevRevealed))
          currentIteration += 1

          if (currentIteration >= maxIterations) {
            clearInterval(interval)
            setIsAnimating(false)
            setDisplayText(text)
            setIsDecrypted(true)
          }

          return prevRevealed
        }

        let currentSet = prevRevealed
        if (currentSet.size === 0) {
          currentSet = fillAllIndices()
        }

        const removeCount = Math.max(1, Math.ceil(text.length / Math.max(1, maxIterations)))
        const nextSet = removeRandomIndices(currentSet, removeCount)
        setDisplayText(shuffleText(text, nextSet))
        currentIteration += 1

        if (nextSet.size === 0 || currentIteration >= maxIterations) {
          clearInterval(interval)
          setIsAnimating(false)
          setIsDecrypted(false)
          setDisplayText(shuffleText(text, new Set()))
          return new Set()
        }

        return nextSet
      })
    }, speed)

    return () => clearInterval(interval)
  }, [
    isAnimating,
    text,
    speed,
    maxIterations,
    sequential,
    revealDirection,
    shuffleText,
    direction,
    fillAllIndices,
    removeRandomIndices,
  ])

  const handleClick = () => {
    if (animateOn !== 'click') {
      return
    }

    if (clickMode === 'once') {
      if (isDecrypted) {
        return
      }
      setDirection('forward')
      triggerDecrypt()
      return
    }

    if (isDecrypted) {
      triggerReverse()
    } else {
      setDirection('forward')
      triggerDecrypt()
    }
  }

  const triggerHoverDecrypt = useCallback(() => {
    if (isAnimating) {
      return
    }

    setRevealedIndices(new Set())
    setIsDecrypted(false)
    setDisplayText(text)
    setDirection('forward')
    setIsAnimating(true)
  }, [isAnimating, text])

  const resetToPlainText = useCallback(() => {
    setIsAnimating(false)
    setRevealedIndices(new Set())
    setDisplayText(text)
    setIsDecrypted(true)
    setDirection('forward')
  }, [text])

  useEffect(() => {
    if (animateOn !== 'view' && animateOn !== 'inViewHover') {
      return
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !hasAnimated) {
            triggerDecrypt()
            setHasAnimated(true)
          }
        })
      },
      {
        root: null,
        rootMargin: '0px',
        threshold: 0.1,
      },
    )

    const currentRef = containerRef.current
    if (currentRef) {
      observer.observe(currentRef)
    }

    return () => {
      if (currentRef) {
        observer.unobserve(currentRef)
      }
      observer.disconnect()
    }
  }, [animateOn, hasAnimated, triggerDecrypt])

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      if (animateOn === 'click') {
        encryptInstantly()
      } else {
        setDisplayText(text)
        setIsDecrypted(true)
      }

      setRevealedIndices(new Set())
      setDirection('forward')
    }, 0)

    return () => {
      window.clearTimeout(timeout)
    }
  }, [animateOn, text, encryptInstantly])

  const animateProps =
    animateOn === 'hover' || animateOn === 'inViewHover'
      ? {
          onMouseEnter: triggerHoverDecrypt,
          onMouseLeave: resetToPlainText,
        }
      : animateOn === 'click'
        ? {
            onClick: handleClick,
          }
        : {}

  return (
    <motion.span
      ref={containerRef}
      className={`inline-block whitespace-pre-wrap ${parentClassName}`}
      {...animateProps}
      {...props}
    >
      <span className="sr-only">{displayText}</span>
      <span aria-hidden="true">
        {displayText.split('').map((char, index) => {
          const isRevealedOrDone = revealedIndices.has(index) || (!isAnimating && isDecrypted)
          return (
            <span key={index} className={isRevealedOrDone ? className : encryptedClassName}>
              {char}
            </span>
          )
        })}
      </span>
    </motion.span>
  )
}
