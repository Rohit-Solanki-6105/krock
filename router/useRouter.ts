"use client"

import { useState, useEffect } from "react"

export function useRouter() {

    const isBrowser = typeof window !== "undefined"

    const [pathname, setPathname] = useState("")
    const [query, setQuery] = useState<URLSearchParams>(new URLSearchParams())
    const [params, setParams] = useState<any>({})

    useEffect(() => {

        if (!isBrowser) return

        setPathname(window.location.pathname)
        setQuery(new URLSearchParams(window.location.search))
        setParams((window as any).__PARAMS__ || {})

    }, [])

    function push(path: string) {

        if (!isBrowser) return

        window.location.href = path
    }

    function replace(path: string) {

        if (!isBrowser) return

        window.location.replace(path)
    }

    function back() {

        if (!isBrowser) return

        window.history.back()
    }

    function forward() {

        if (!isBrowser) return

        window.history.forward()
    }

    function reload() {

        if (!isBrowser) return

        window.location.reload()
    }

    return {
        pathname,
        query,
        params,
        push,
        replace,
        back,
        forward,
        reload
    }
}
