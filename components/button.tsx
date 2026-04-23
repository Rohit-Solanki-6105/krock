import React, { useEffect } from 'react'

function Button({children}:{children: React.ReactNode}) {
    return (
        <button onClick={() => alert("clicked")}>
            {children}
        </button>
    )
}

export default Button
