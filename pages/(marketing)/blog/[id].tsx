import React from 'react';

export default function BlogPost({ params }:{ params: { id: string } }) {
    return (
        <div>
            <h1>Post ID: {params.id}</h1>
            <p>Welcome to the dynamic post page.</p>
        </div>
    );
}