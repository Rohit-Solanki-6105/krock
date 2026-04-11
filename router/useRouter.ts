"use server"
import { useState, useEffect } from "react"

export function useRouter() {
    const [pathname, setPathname] = useState(window.location.pathname)
    const [query, setQuery] = useState(
        new URLSearchParams(window.location.search)
    )

    useEffect(() => {
        setPathname(window.location.pathname)
        setQuery(new URLSearchParams(window.location.search))
    }, [])

    function push(path: string) {
        window.location.href = path
    }

    function replace(path: string) {
        window.location.replace(path)
    }

    function back() {
        window.history.back()
    }

    function forward() {
        window.history.forward()
    }

    function reload() {
        window.location.reload()
    }

    return {
        pathname,
        query,
        params: (window as any).__PARAMS__ || {},
        push,
        replace,
        back,
        forward,
        reload
    }
}