import { useRouter } from "@/router/useRouter";
import React from "react";
// import "./globals.css"
export default function Layout({ children }:{ children: React.ReactNode }) {
    const { pathname } = useRouter();
    const navigate = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
        // This is a simple version of "Client Side Routing"
        // For now, standard links are fine, but adding a loading state helps!
        console.log("Navigating to:", href);
    };


    return (
        <div style={{ fontFamily: 'system-ui', maxWidth: '800px', margin: 'auto' }}>
            <nav style={{ display: 'flex', gap: '1rem', padding: '1rem 0', borderBottom: '1px solid #eee' }}>
                <a href="/" style={{
                    background: pathname == "/" ? "black" : "white"
                }}>Home</a>
                <a href="/about" className="bg-black">About</a>
                <a href="/contact">Contact</a>
            </nav>
            <main style={{ padding: '2rem 0' }}>{children}</main>
        </div>
    );
}