import React from 'react'

function layout({ children }: { children: React.ReactNode }) {
    return (
        <div>
            Marketing
            {children}
        </div>
    )
}

export default layout
