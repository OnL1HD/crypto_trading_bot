import { useEffect, useState } from 'react'
import { Footer } from './components/layout/Footer'
import { TopNavbar } from './components/layout/TopNavbar'
import { ExecutionPage } from './pages/ExecutionPage'
import { HomePage } from './pages/HomePage'
import { MarketPage } from './pages/MarketPage'
import { ModelPage } from './pages/ModelPage'
import { SystemPage } from './pages/SystemPage'

type AppPath = '/' | '/market' | '/model' | '/execution' | '/system'

function resolvePath(pathname: string): AppPath {
  if (pathname === '/market') {
    return '/market'
  }
  if (pathname === '/model') {
    return '/model'
  }
  if (pathname === '/execution') {
    return '/execution'
  }
  if (pathname === '/system') {
    return '/system'
  }
  return '/'
}

function App() {
  const [path, setPath] = useState<AppPath>(() => resolvePath(window.location.pathname))
  const [hash, setHash] = useState<string>(() => window.location.hash)

  useEffect(() => {
    const handleLocationChange = () => {
      setPath(resolvePath(window.location.pathname))
      setHash(window.location.hash)
    }

    window.addEventListener('popstate', handleLocationChange)
    return () => window.removeEventListener('popstate', handleLocationChange)
  }, [])

  useEffect(() => {
    if (path !== '/' || hash === '') {
      window.scrollTo({ top: 0, behavior: 'auto' })
      return
    }

    const targetId = hash.replace('#', '')
    const timeoutId = window.setTimeout(() => {
      document.getElementById(targetId)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 60)

    return () => window.clearTimeout(timeoutId)
  }, [hash, path])

  const handleNavigate = (nextPath: string, nextHash?: string) => {
    const resolvedPath = resolvePath(nextPath)
    const url = `${resolvedPath}${nextHash ?? ''}`
    window.history.pushState({}, '', url)
    setPath(resolvedPath)
    setHash(nextHash ?? '')
  }

  let content = <HomePage onNavigate={handleNavigate} />

  if (path === '/market') {
    content = <MarketPage />
  } else if (path === '/model') {
    content = <ModelPage />
  } else if (path === '/execution') {
    content = <ExecutionPage />
  } else if (path === '/system') {
    content = <SystemPage />
  }

  return (
    <>
      <TopNavbar currentPath={path} onNavigate={handleNavigate} />
      {content}
      <Footer onNavigate={handleNavigate} />
    </>
  )
}

export default App
